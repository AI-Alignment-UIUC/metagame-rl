# How large game-AI systems learned rare but important actions from self-play (without human data)

Application context: a Pokémon TCG self-play pilot rarely plays deck-search and recovery Trainers (Computer Search, Item Finder) and values them below a basic Energy, even as overall strength improves.

Source-reading legend: **[full text]** = paper body read this session (via ar5iv HTML); **[snippet]** = only search-result snippets or a summary page read; **[memory]** = not re-read this session, from prior knowledge; verify before quoting. Human-data flags: **HUMAN DATA** = trained on human games/moves/statistics (exclude from recommendations); **PRIVILEGED** = trains with hidden-information or oracle features; **CLEAN** = self-play only (game rules plus generic design).

## OpenAI Five (Dota 2): how rare items and abilities were learned, and what was scripted or shaped

### Takeaway
OpenAI Five did **not** learn item purchasing, ability builds, item swaps or courier control. Those were scripted, and item randomization in training drew on human item builds. What it did learn from self-play (item and spell *use*, targeting) worked through four things: a factored action space with masking, a **separate targeting head for one rare action (Teleport) whose signal was otherwise "drowned out"**, environment randomization aimed at behaviors the agent had learned to avoid (Roshan), and an entropy bonus of 0.01. It also documents the failure mode in this project: a hero whose skill the pilot used badly got low value in the drafting preferences.

### Cited Findings
- **Scripted, not learned [full text]:** "the order in which heroes purchase items and abilities, control of the unique courier unit, and which items heroes keep in reserve" were hand-scripted. The authors note they "achieved superhuman performance before" replacing them, and Section 5 still lists "certain sub-systems hard-coded (such as item buying)." — [Berner et al. 2019, arXiv:1912.06680](https://arxiv.org/abs/1912.06680)
- **Appendix F's scripted-action list [full text]:**
  - ability builds: a fixed level-up schedule, randomized "somewhat" in training;
  - item purchasing: consumables kept stocked until a set time, other items on a fixed build;
  - item swap: a heuristic keeps valuable items in inventory;
  - courier: a state machine.

  The authors "believe the agent could perform better without them." — [arXiv:1912.06680](https://arxiv.org/abs/1912.06680)
- **The one HUMAN DATA use [full text]:** in training, non-consumable items are randomly deleted from the fixed build order and replaced with items "sampled from how humans usually buy that hero's items." The authors call this the only place the system uses human-game data. The reward function was also designed from "team members' familiarity with the game." — [arXiv:1912.06680](https://arxiv.org/abs/1912.06680)
- **Moved from script to policy by "surgery" [full text]:** Buyback became model-controlled, and "consumables on allies" was added as an action (12/14/2018). Bottle and Divine Rapier were added late. — [arXiv:1912.06680](https://arxiv.org/abs/1912.06680)
- **Rare action got its own head [full text]:** Teleport has a dedicated unit-selection head because it is rare and its signal would otherwise be "drowned out" in the shared targeting head. Offsets are similarly split into regular, caster and ward-placement heads. — [arXiv:1912.06680](https://arxiv.org/abs/1912.06680)
- **Action space [full text]:**
  - Primary actions average about 8.1 available per step (noop, move, attack, spells, items, situational actions such as Buyback, Shrine, Purchase).
  - Parameters: delay (4 values), unit selection (189), offset (9×9 = 81 values).
  - "Simple action filters" mask unavailable actions (no valid target, on cooldown), and ignored parameters are masked from gradients.
  - The full factorized space is up to 1,837,080 dimensions, with 8,000–80,000 available actions per hero per step.

  — [arXiv:1912.06680](https://arxiv.org/abs/1912.06680)
- **Exploration settings [full text]:**
  - Entropy coefficient 0.01 performed best. 0 early "does not completely prevent learning," and higher entropy was much worse. Rerun lowered it to 0.001.
  - Team spirit was annealed from 0.3 to 1.0.

  — [arXiv:1912.06680](https://arxiv.org/abs/1912.06680)
- **Randomization targeted at avoided behaviors [full text]:**
  - **Roshan health** was randomized between zero and full because agents had learned "never to approach this creature."
  - **Lane assignments** were randomized after agents got stuck moving as a five-stack (an ablation later suggested this "may not have been necessary").
  - Initial level, gold and stats, hero lineups and items were also randomized.
  - The stated rationale: agents might "quickly learn never to take a new action" and so fail to learn dependent skills. Randomization avoids long, specific action sequences that agents would never explore.

  — [arXiv:1912.06680](https://arxiv.org/abs/1912.06680)
- **Pilot skill limited draft value [full text]:** Earthshaker's agent "had trouble dealing with geometry" of Fissure, making the hero weaker in rollouts and giving it low value in the drafting preferences. — [arXiv:1912.06680](https://arxiv.org/abs/1912.06680)
- **Rare high-variance item destabilized training [full text]:** adding Divine Rapier mid-Rerun "could cause the agents to enter a negative feedback loop" and TrueSkill stopped improving; banning it restored progress. The authors hypothesize that the item's transfer-on-death raised reward variance. Gradually adding new actions also sometimes caused instability, "including the agent avoiding new actions entirely." — [arXiv:1912.06680](https://arxiv.org/abs/1912.06680)
- **Reward shaping (Appendix G, Table 5) [full text, values as extracted]:**
  - Win 5; hero death −1; courier death −2; XP 0.002; gold gained 0.006; gold spent 0.0006; health changed 2 (quartic); mana changed 0.75.
  - Killed hero −0.6; last hit −0.16; deny 0.15.
  - Aegis 5; Ancient HP 5; Megas 4; towers T1/T2/T3/T4 = 2.25/3/4.5/2.25; Shrine 2.25; Barracks 6; wrong-lane −0.15 per second.
  - Rewards are zero-sum (opponent's subtracted), and non-win rewards are multiplied by 0.6^(T/10 min).

  The paper reports that without partial rewards the agent still beat a scripted bot but was much less sample-efficient. — [arXiv:1912.06680](https://arxiv.org/abs/1912.06680)
- **Comparison MOBA, Honor of Kings (Tencent) [full text]:** reward table includes gold 0.005, XP 0.001, mana 0.05, HP 3, kill 1, death −1, etc. It uses action masks "to eliminate unnecessary RL explorations," dual-clip PPO (ε = 0.2, c = 3), hierarchical What/Who/How heads assumed independent, and "Item skill" as an action type. The paper does not say how item *purchasing* is handled. HUMAN DATA: lineup win rates "obtained from the vast amount of human player data" were used to balance the curriculum's hero groups. Results: 40/42 wins against pro teams, 97.7% over 642,047 public matches. — [Ye et al. 2020, arXiv:2011.12692](https://arxiv.org/abs/2011.12692)

### Inferences
- The closest analog to this project's problem is Earthshaker: a pilot that executes a card's sub-decisions badly produces low rollout value, so the draft head learns a low value. Computer Search being valued below a basic Energy is consistent with the pilot's *execution* of the card (which 2 cards to discard, which card to fetch) being poor rather than with the draft head being wrong. Fixing the pilot comes first. This matches Evan's rule to fix how the agent learns.
- The Teleport-head finding transfers directly. If Computer Search's "choose card from deck" and Item Finder's "choose Trainer from discard" pointer decisions share a head (and a loss normalization) with frequent decisions such as attach-Energy targeting, their gradient is diluted. A separate head, or per-decision-type loss and advantage normalization, is the documented fix. It is generic and needs no human prior.
- The Roshan randomization is a generic, prior-free pattern: when the agent has learned to *never* take an action, randomize the *environment* (not the policy) so that the action sometimes pays off and gets re-sampled. The TCG analog: randomized initial states (random hand, deck and discard compositions, mid-game starts) in which deck search or discard recovery is high-value. This uses no human decklists.
- OpenAI Five avoided the hardest rare-decision problem (purchasing, which resembles drafting) by scripting it. Its success therefore says little about learning purchase or draft value from scratch. Do not cite it as evidence that this is easy.
- The Divine Rapier episode warns that adding a high-variance rare action can push training into avoidance. Ramp such cards in gradually, or monitor return variance when they appear.

### Gaps
- The paper gives no per-item learning curves or frequency statistics, so there is no direct evidence on how fast rarely used *consumables* or items were learned through self-play.
- Honor of Kings item-purchase handling was not stated in the paper body read. From memory, later JueWu work used learned or human-derived equipment systems; unverified.

## AlphaStar (StarCraft II): league training, exploiters, rare strategies, and the role of human data

### Takeaway
AlphaStar's rare-strategy coverage depended heavily on human data:
- supervised initialization on 971k replays;
- a strategy statistic z sampled from human games;
- pseudo-rewards for following human build orders;
- KL distillation toward the supervised policy.

DeepMind states that without it there was "almost no chance" of finding successful strategies. The CLEAN, transferable part is the **league structure**: main agents, plus main exploiters and league exploiters that are periodically reset, trained with prioritized fictitious self-play. TStarBot-X, a follow-up, found that PFSP alone collapses to one or two rushes within days, and that **specialized exploiters** recovered unit and tech diversity.

### Cited Findings
- **HUMAN DATA scale and statement [snippet]:** imitation learning gave an initial agent that "played the game better than 84% of active players." Without prior knowledge there would be "almost no chance" of finding successful strategies, and "Learning human strategies, and ensuring that the agents keep exploring those strategies" was key. A latent variable encodes "the distribution of opening moves from human games." Final rank was above 99.8% of active Battle.net players. — [DeepMind AlphaStar blog](https://deepmind.google/discover/blog/alphastar-grandmaster-level-in-starcraft-ii-using-multi-agent-reinforcement-learning/)
- **HUMAN DATA mechanics [full text of TStarBot-X's recap of AlphaStar]:** AlphaStar used 971,000 human replays. The z-stat fixes a build-order sequence, unit coordinates and a unit-appearance vector. Rewards add build-order edit distance and distances to z targets, active with probability 0.25 for the main agent. The RL loss includes distillation toward the supervised model. Compute: 3,072 TPU cores, 50,400 CPU cores, 44 days. — [Han et al. 2020, TStarBot-X, arXiv:2011.13729](https://arxiv.org/abs/2011.13729)
- **League roles [full text, TStarBot-X recap]:** "AlphaStar's league contains three agent roles: Main Agent (MA), Main Exploiter (ME) and League Exploiter (LE)": one MA per race, each with one ME and two LEs. — [arXiv:2011.13729](https://arxiv.org/abs/2011.13729)
- **League details [memory]:**
  - Main agents train 35% against themselves, 50% with PFSP against all past players and 15% against forgotten or exploiter players.
  - PFSP weights opponents by f_hard(x) = (1−x)^p, where x is the agent's win rate.
  - Main exploiters train only against current main agents and are reset to the supervised policy when they reach about 70% win rate or after a step budget. League exploiters reset with probability 0.25.
  - The Nature paper's ablations reported large drops without human data and without exploiters; exact numbers not verified this session.

  — [Vinyals et al. 2019, Nature](https://www.nature.com/articles/s41586-019-1724-z) (paywalled; not read)
- **PFSP alone collapses [full text]:** in TStarBot-X, without intervention "the main agent converges to either Zergling Rush or Roach Push" within a few days. Because of SC2's cyclic, non-transitive strategy space, "using PFSP is not sufficient to let the agent discover robust or novel policies." The paper notes that key state-action pairs may occur only once in thousands of steps, so fitting them takes very many episodes. — [arXiv:2011.13729](https://arxiv.org/abs/2011.13729)
- **What helped in TStarBot-X [full text]:**
  - Specialized exploiters (Specific, Evolutionary and Adaptive Evolutionary exploiters) "produced more varied units, upgrades, and buildings."
  - Rule-guided policy search raised the probability of rule-specified actions (EXPERT RULES).
  - Diversified human replay subsets (Hydralisk, Lurker, Mutalisk, Nydus, worker rush, …) seeded specific exploiters (HUMAN DATA).
  - DAPO, a KL term toward the model from about 12 hours earlier, "significantly improved policy strength" (CLEAN).
  - Scale: 583 agents, 25.7M matches, 57 days.

  — [arXiv:2011.13729](https://arxiv.org/abs/2011.13729)
- **Action space [memory]:** autoregressive heads (action type → delay → queued → selected units via pointer network → target unit or point). — [Nature 2019](https://www.nature.com/articles/s41586-019-1724-z)

### Inferences
- AlphaStar shows that rare *strategies* (tech paths, unusual units) were not found from scratch at that scale. The human z-statistic did that work. It is therefore not evidence that a pure self-play league finds rare strategies, and this project cannot use the z-statistic.
- The transferable, CLEAN parts are:
  - exploiters that train only against the current main agent and are **reset** periodically, so they keep finding the main agent's current weakness;
  - PFSP weighting toward hard opponents;
  - a KL anchor to a recent past self (DAPO-style) for stability.
- For a TCG drafter, a "deck-search exploiter" could be an exploiter whose *deck* is constrained or randomized to contain search and recovery Trainers. It would force the pilot to face and use those lines. This is generic: a randomized-deck constraint, not a human list.
- TStarBot-X's convergence to "Zergling Rush or Roach Push" is the SC2 counterpart of this project's Energy-heavy minimum: a cheap, reliable, low-variance strategy that self-play finds first and then stays in.

### Gaps
- AlphaStar's Nature ablation numbers (no human data, no z, no exploiters) could not be read: the paper is paywalled and the PDF did not parse. They are reported here from memory only, without figures.
- No source found that isolates exploiters' effect on *rare unit* usage in a human-data-free league.

## Card-game agents (Hearthstone, LOCM, MTG, Yu-Gi-Oh!, Pokémon TCG, DouDizhu, Mahjong): learning the value of tutor, search, draw and recovery cards

### Takeaway
No paper found reports a self-play agent learning the value of tutor or search cards specifically. This is a real gap in the literature. The relevant evidence is indirect:
- **DouZero (CLEAN)** handles 27,472 actions, including rare bombs and rockets, by scoring *action features* (a 4×15 card matrix) with Monte-Carlo returns, so values generalize across rarely seen actions.
- **ByteRL's LOCM agent (CLEAN)** learns draft and battle end-to-end with one network and a ±1 reward, trained with optimistic smooth fictitious play, but reports no card-value analysis.
- **Suphx** relies on human data and privileged-information "oracle guiding," and gives its rare decisions (Riichi, Chow, Pong, Kong) separate binary models.
- **DouZero's human-move accuracy rose for about 5 days and then fell.** Stronger self-play drifted away from human play.

### Cited Findings
- **DouZero action encoding [full text, CLEAN]:**
  - Each action is a 4×15 one-hot card matrix, flattened to 54 dimensions and fed *into* the Q-network with the state, so the network "can generalize to unseen actions."
  - Rare types in the 27,472-action space: Bomb (13), Rocket (1), Quad+Solo (1,326), Quad+Pair (858), Plane+Solo (21,822), Plane+Pair (2,939).
  - No human data or domain knowledge in the card-play network. The bidding network and the SL baseline (226,230 expert matches) used human data.

  — [Zha et al. 2021, DouZero, arXiv:2106.06135](https://arxiv.org/abs/2106.06135)
- **DouZero learning method [full text]:**
  - Deep Monte-Carlo with ε-greedy ε = 0.01, γ = 1, RMSprop learning rate 1e-4.
  - MC was chosen because it avoids DQN overestimation with large action spaces and is unaffected by long horizons with end-of-game reward.
  - Deep SARSA learned slightly slower, and actor-critic failed.
  - Ranked first of 344 bots on Botzone (Elo 1625) after 30 days. It beat the SL baseline within about 2 days and DeltaDou within about 10.

  — [arXiv:2106.06135](https://arxiv.org/abs/2106.06135)
- **DouZero vs human moves [full text]:** accuracy against human moves rose during the first five days of training, then fell sharply. The authors read this as DouZero first matching human strategy, then finding strategies humans do not use. Agents trained on win probability played bombs more aggressively than agents trained on score (ADP). No dedicated analysis of rare-action learning. — [arXiv:2106.06135](https://arxiv.org/abs/2106.06135)
- **ByteRL LOCM [full text, CLEAN]:**
  - One network outputs the card-building (draft) policy, the battle policy and the value. "each entire game [is] a trajectory, which contains both CB stage and BT stage."
  - Draft: a masked categorical pick over 30 steps. Battle: a single categorical over all actions with an illegal-action mask. Per-card embeddings are shared, and deck embeddings are mean-pooled. Reward ±1 at game end.
  - Optimistic smooth fictitious play (self-play probability 0.6, history-add threshold 0.7) was chosen because plain fictitious-play iterates "can cycle around NE."
  - Won both COG 2022 LOCM tracks (84.4% and 94.6% average win rate). Compute: 24 units (GPU plus 600 CPU cores) for about 72 h.
  - **No analysis of drafted card values, draw cards or mana curve.**

  — [Xi et al. 2023, arXiv:2303.04096](https://arxiv.org/abs/2303.04096)
- **Suphx (Mahjong) [full text], HUMAN DATA + PRIVILEGED:**
  - Five models (discard, Riichi, Chow, Pong, Kong), each first trained by supervised learning on top Tenhou players. Samples: 15M discard, 5M Riichi, 10M Chow, 10M Pong, 4M Kong. Winning is decided by a rule.
  - RL refined **only the discard model** in the experiments. The rare-decision models kept their supervised weights.
  - **Oracle guiding**: the agent first sees opponents' hands and the wall, then those features are dropped with Bernoulli dropout decaying from 1 to 0. Afterward, training continues at one-tenth the learning rate and rejects samples with large importance weights.
  - **Global reward prediction**: a GRU predicts the final game reward from round features, and each round's reward is Φ(x_k) − Φ(x_{k−1}). This is credit assignment across 8–12 rounds.
  - Results: 8.74 stable dan vs 7.46 for top humans; simple distillation from the oracle "worked poorly."

  — [Li et al. 2020, Suphx, arXiv:2003.13590](https://arxiv.org/abs/2003.13590)
- **Pokémon TCG, cabt engine (Kaggle competition) [summary page]:**
  - PPO self-play agents, one fixed deck each, about 0.5M parameters.
  - Pointer-style head over the engine's variable-length legal-option list. Multi-select decisions become sequential picks with a learned STOP.
  - Potential-based shaping on prize differential. One checkpoint uses expert iteration with IS-MCTS (determinization) targets.
  - Results only vs a random agent (100% over 20 games for one deck). No analysis of Trainer use.

  — [TomatoCream/pkm-cabt-ppo](https://huggingface.co/TomatoCream/pkm-cabt-ppo)
- **Other Pokémon TCG work [snippet only]:** a thesis trains PPO and DQN self-play on a *simplified* PTCG with legality masks and shaped rewards (PPO more stable). Separately, a Kaggle PTCG bot competition used the LibCABT engine with rules-based starter agents. — [NCF thesis](https://digitalcommons.ncf.edu/theses_etds/7022); [competitor blog](https://cosmiccreature.mataroa.blog/blog/cosmics-ptcg-competition-1/)
- **Yu-Gi-Oh! [snippet only]:** ygo-agent (sbl1996) is an RL agent on ygopro-core via an envpool gym interface, described as using RL plus LLMs. Its self-play details are unconfirmed (aggregator pages only). — [ygo-agent](https://github.com/sbl1996/ygo-agent)

### Inferences
- DouZero's lesson for rare actions is representational. Score a candidate action by its *content features*, so a rarely chosen action still gets an informed value from similar actions. For the pilot, "play Computer Search" should be represented by what it does and by the candidate cards it could fetch or discard. A per-card-ID logit that is rarely updated learns slowly.
- DouZero's MC-over-TD result supports full-episode returns for long-horizon, end-of-game reward. The cost is variance: a search card played on turn 2 is credited with the whole game's noise. Suphx's global reward prediction (a learned potential over game progress, with per-segment differences) is a CLEAN credit-assignment idea once its human-data initialization is set aside. It resembles potential-based shaping with a *learned* potential, as cabt does with prize differential.
- Suphx did not solve rare decisions with RL. It used human data and left the rare-decision models supervised, so it offers no CLEAN recipe for them. Oracle guiding is PRIVILEGED. It may or may not count as "oracle answers" under Evan's rule: the oracle provides inputs, not target actions. Flag it for Evan rather than recommend it.
- The DouZero accuracy curve (matching human moves, then drifting away) warns about this project's ground-truth objective. Better self-play does not imply convergence toward human choices, so decklist agreement should be tracked as a separate metric from strength. See also DORA below.

### Gaps
- Found no paper measuring how a self-play card-game agent learns to value tutor, search, draw or recovery cards, or how often it plays them. Searches did not reach Hearthstone self-play RL or MTG RL papers this session. From memory, Hearthstone deck-space work (e.g. MAP-Elites over decks with scripted pilots, Fontaine et al. 2019) uses scripted game AIs, not learned pilots; unverified.
- ygo-agent and the Kaggle cabt agents publish no Trainer-usage analysis.

## Poker (Libratus, Pluribus, DeepStack, ReBeL): how rare lines are covered and what transfers to an RL pilot

### Takeaway
All four poker systems are CLEAN in training: no human hands. Rare lines are covered by four mechanisms:
- **sampling schemes that keep every action reachable**: MCCFR external or outcome sampling, where outcome sampling uses ε-exploration plus importance weights;
- **pruning that is never permanent**: Pluribus skips very-negative-regret actions in 95% of iterations, explores everything in 5%, and floors regret at −310M so pruned actions can come back;
- **forced off-policy exploration in self-play data generation**: ReBeL has one agent take a random action with ε = 0.25;
- **training value nets on broadly sampled situations**: DeepStack, from memory.

The transferable pattern is the second: periodically re-evaluate actions the policy has written off, and bound how negative their value can get.

### Cited Findings
- **Pluribus pruning [snippet of Science paper and supplement]:**
  - Blueprint computed by Linear MCCFR self-play. Linear weighting (iteration T weighted by T) was used for both regrets and average strategy for the first 400 minutes.
  - Actions with extremely negative regret "are not explored in 95% of iterations."
  - "there was also a floor on regret at −310,000,000 for every action. This made it easier to unprune actions that were initially pruned but later improved."
  - The authors "suspect this sped up convergence by about a factor of 3" (their estimate, not measured).

  — [Brown & Sandholm 2019, Science](https://www.science.org/doi/10.1126/science.aay2400); [supplement](https://noambrown.com/papers/19-Science-Superhuman_Supp.pdf)
- **Origin of regret-based pruning [snippet]:** a negative-regret path is skipped and revisited at the earliest iteration at which its regret could have become positive, preserving CFR's convergence guarantees. — [Brown & Sandholm 2015, NeurIPS](https://proceedings.neurips.cc/paper/2015/hash/c54e7837e0cd0ced286cb5995327d1ab-Abstract.html)
- **ReBeL exploration [full text, CLEAN]:**
  - One agent takes a uniformly random action with probability ε = 0.25 during self-play training (ε = 0 at test), "To ensure sufficient exploration."
  - Exploring with only *one* agent is more efficient, because leaves reachable only when both go off-policy are irrelevant.
  - Bet sizes are perturbed by ±0.1× pot during training for diversity.
  - A value net trained on *random* beliefs "fails to learn anything valuable."
  - Leaves that neither player reaches with positive probability do not affect results.

  Results: beats Dong Kim by 165 ± 69 mbb/g; Liar's Dice exploitability about 0.015–0.024. — [Brown et al. 2020, ReBeL, arXiv:2007.13544](https://arxiv.org/abs/2007.13544)
- **MCCFR sampling schemes [memory]:**
  - *External sampling* explores every action of the traversing player and samples chance and opponent actions.
  - *Outcome sampling* samples a single trajectory using an exploratory sampling policy (the current strategy mixed with uniform at rate ε, often about 0.6 in experiments) and corrects with importance weights 1/q(z), so every action keeps positive sampling probability.

  — Lanctot et al. 2009, "Monte Carlo Sampling for Regret Minimization in Extensive Games," NeurIPS (URL not verified this session)
- **DeepStack [memory]:** counterfactual value networks trained on about 10M randomly generated poker situations with random ranges and pot sizes, so rarely reached situations still have training data. — [Moravčík et al. 2017, arXiv:1701.01724](https://arxiv.org/abs/1701.01724)
- **Libratus [memory]:** its "self-improver" added bet sizes that opponents (human pros) actually used, computed overnight during the match. That uses human *opponent* actions at play time, so treat it as HUMAN DATA for this project's purposes. — [Brown & Sandholm 2018, Science](https://www.science.org/doi/10.1126/science.aao1733)

### Inferences
- **Never-permanent pruning carries over directly to RL.** PPO's softmax plus entropy decay can drive Computer Search's play probability to about 0. The Pluribus analog:
  - a floor on each legal action's logit or probability within a decision type (the regret floor);
  - plus a small fraction of episodes (for example 5%) in which the exploring seat samples uniformly among legal Trainer plays.

  Both are generic, with no card-specific prior.
- **One-sided exploration (ReBeL)** carries over to an RL pilot: give one seat per game a raised ε on legal actions, and either exclude that seat's off-policy steps from the policy-gradient loss or importance-weight them (outcome-sampling style). Its returns still train the value/Q head on states where a search card was played. This produces value-learning data for rare lines without corrupting the policy target.
- ReBeL's warning that random beliefs teach nothing suggests that exploration should stay *near* on-policy states (one off-policy action, then on-policy continuation). Fully random states help little.
- Poker's coverage tools lean on CFR's tabular or regret structure. With PPO, the closest equivalents are a Q- or advantage-head over *all legal actions* (so unplayed actions still get evaluated, as in DouZero) and occasional forced evaluation of low-probability actions.

### Gaps
- Pluribus's exact exceptions to pruning (e.g. river, terminal nodes) could not be confirmed. The PDFs did not parse, and a reimplementation claims pruning is never applied on the river, which is not authoritative.
- No poker paper measured the learning of specific *rare but strong* lines as an outcome. The evidence is about convergence speed and exploitability.

## Cross-cutting lessons: action factoring, curricula, restarts, population diversity, targeted exploration

### Takeaway
Across systems, five CLEAN mechanisms made rare actions learnable:
1. A **separate or factored head**, or per-type normalization, for rare decisions (OpenAI Five Teleport; Suphx's separate models).
2. **Content-based action scoring**, so values generalize to rarely tried actions (DouZero; pointer heads in cabt and AlphaStar).
3. **Guaranteed minimum re-evaluation of written-off actions, with a correction so the policy target is not polluted**: KataGo forced playouts plus policy target pruning (about 1.25× training efficiency); the Pluribus 5%-unpruned rule plus regret floor; ReBeL one-sided ε = 0.25.
4. **Environment or initial-state randomization aimed at behaviors the agent has learned to avoid** (OpenAI Five's Roshan health).
5. **Population pressure from reset exploiters** (AlphaStar, TStarBot-X).

Two cautions apply. Rare tactics can be learned very late (AlphaGo Zero ladders, from memory). And pure self-play can settle in an equilibrium far from human conventions (DORA, Diplomacy; DouZero's drift).

### Cited Findings
- **KataGo forced playouts [full text, CLEAN search technique; game-specific input features flagged]:**
  - Each root child that has been visited gets at least n_forced(c) = sqrt(k · P(c) · Σ N), with k = 2.
  - Motivation: Dirichlet noise sometimes surfaces a move that is actually good, but its first evaluation is negative, so search never explores it again.
  - **Policy target pruning** removes those forced visits from the policy training target, so exploration does not leak into the learned policy.
  - Ablation: removing both drops Elo from 1329 to 1276, about a 1.25× training-time factor.
  - Playout cap randomization (full search with probability 0.25, and only full-search turns train the policy) gave about 1.37×.
  - Root Dirichlet noise: P = 0.75 · P_raw + 0.25 · η, with α = 0.03 · 19²/N_legal.
  - KataGo also uses **hand-crafted ladder features** (game-specific priors; not CLEAN by this project's standard).

  — [Wu 2019, KataGo, arXiv:1902.10565](https://arxiv.org/abs/1902.10565)
- **Late learning of a rare tactic [memory]:** AlphaGo Zero reportedly understood ladders (shicho) "only much later in training," although humans learn them first. — [Silver et al. 2017, Nature](https://www.nature.com/articles/nature24270)
- **Gumbel top-k at the root [memory]:** Gumbel AlphaZero/MuZero samples k actions without replacement using Gumbel noise and sequential halving at the root. It guarantees policy improvement even with very few simulations, so low-prior actions still get evaluated. — [Danihelka et al. 2022, ICLR](https://openreview.net/forum?id=bERaNdoegnO)
- **Curriculum by fixed sub-populations, then distillation [full text]:** Honor of Kings' CSPL trains teachers on fixed 10-hero groups, distills them into one student, then continues on random lineups. It converged in 336 h, versus over 480 h without converging for the baseline. "Presenting disordered agent combinations for training leads to degraded performance." HUMAN DATA only in balancing the groups by human lineup win rates; self-play win rates could replace it. — [arXiv:2011.12692](https://arxiv.org/abs/2011.12692)
- **Self-play reaches a non-human equilibrium [abstract or summary only]:** DORA reaches superhuman 2-player no-press Diplomacy "without any human data or reward shaping." In 7-player it "approximates an equilibrium that differs radically from human-data-based agents," and "there may be a wide space of equilibria, with some differing dramatically from human conventions." DORA augments proposed actions with exploratory actions found by a double-oracle process; actions found useful are learned by the proposal network. — [Bakhtin et al. 2021, arXiv:2110.02924](https://arxiv.org/abs/2110.02924)
- **Self-play rediscovering human knowledge over training [memory]:** McGrath et al. probe AlphaZero's chess network and find that human concepts and opening preferences emerge over training. Opening choices shift during training and converge partly, but not fully, to human theory. — [McGrath et al. 2022, PNAS](https://www.pnas.org/doi/10.1073/pnas.2206625119)
- **The opposite of rare-action learning [memory]:** DeepNash (Stratego, CLEAN R-NaD self-play) applies fine-tuning and test-time thresholding that zero out very low-probability actions to remove residual mistakes. Thresholding helps play quality, but if applied during training it would suppress rare actions. — [Perolat et al. 2022, arXiv:2206.15378](https://arxiv.org/abs/2206.15378)

### Inferences
Ranked CLEAN, generic options for the pilot's undervaluation of Computer Search and Item Finder:
1. **Diagnose execution first (Earthshaker effect).** Measure the pilot's win-rate delta when it plays the card versus holding it in matched states, and the quality of its sub-choices (discard pair, fetched card). If execution is poor, low draft value is the expected *consequence* and the fix is in the pilot.
2. **Separate head or per-decision-type normalization** for "choose card from deck/discard" and "choose cards to discard" (OpenAI Five Teleport).
3. **Q- or advantage-scoring of all legal options from card-content features** (DouZero), so unplayed Trainers still get value estimates.
4. **Never-permanent suppression**: a floor on per-type play probability plus a small share of games with one-sided forced Trainer exploration, either importance-weighted or excluded from the policy loss (Pluribus, ReBeL, outcome sampling). If the pilot uses IS-MCTS, use forced playouts with policy target pruning, or Gumbel top-k at the root (KataGo, Gumbel MuZero).
5. **Targeted state randomization** (Roshan-style): random mid-game starts or hand/deck/discard compositions where search or recovery pays off.
6. **Exploiters with randomized deck constraints** (AlphaStar, TStarBot-X).
7. **A specialist-then-distill curriculum** (Honor of Kings CSPL): train on fixed deck groups, then distill into one pilot.

Caution on the ground truth: DORA and DouZero both show that stronger self-play can move *away* from human conventions. Track decklist agreement with the human lists as its own metric and do not assume strength gains will close the gap.

### Gaps
- No source directly measures "rare action frequency vs training time" for any of these systems except DouZero's aggregate human-accuracy curve.
- AlphaGo Zero's ladder statement, Gumbel MuZero, DeepNash thresholding, McGrath et al., the MCCFR sampling schemes, DeepStack and Libratus are from memory and were not re-read this session.
- Project research notes already cover adjacent material (population game theory, search and credit, oracle critics, return decomposition) under `research_notes/`. This file does not re-check them for overlap.
