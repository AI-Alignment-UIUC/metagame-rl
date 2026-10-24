# AI for deck-building and collectible card games: deck/draft learning, deck-and-play co-learning, agent-dependent deck evaluation

Failure-mode tags used throughout: F1 collapse to one deck type (walls); F2 pilot/deck co-adaptation; F3 draft-learner collapse and noisy selection; F4 pilot weak over long horizons, search distillation failed; F5 from scratch, everything collapses to Pokemon piles that win by deck-out; F6 turn-limit draws did not help.

## Deck-building methods (evolutionary, MAP-Elites, RL drafting, Q-DeckRec, MTG draft bots) and their results

### Takeaway
Almost every published deck builder optimises decks for a fixed scripted or greedy agent against a fixed set of opponent decks. They all "beat" their baselines, often including human-made decks, under that agent. The methods that keep several deck types alive do it explicitly, with quality-diversity archives (MAP-Elites with sliding boundaries, surrogate-assisted MAP-Elites), not with a single population under fitness selection. RL drafting works, but the drafts it learns are tied to the battle agent it was trained with.

### Cited Findings
- **Fontaine, Lee, Soros, de Mesentier Silva, Togelius, Hoover, "Mapping Hearthstone Deck Spaces through MAP-Elites with Sliding Boundaries", GECCO 2019.**
  - Method: MAP-Elites with Sliding Boundaries (MESB) places cell boundaries at evenly spaced percentiles of the observed distribution of behaviour values instead of at uniform intervals. Boundaries are recomputed every δ=100 individuals (ξ=∞). This avoids "overpopulating cells with conflated behaviors."
  - Behaviour descriptors: average and variance of mana cost, computed from the deck itself.
  - Agents: the SabberStone agent with two strategy heuristics, aggro and control, for three classes.
  - Budget: 200 games per evaluation, 10,000 evaluations per configuration, 500 CPU nodes.
  - Results: card frequencies among elites, e.g. Sunwalker in 99% of control-paladin elites (28.8% after a nerf) and Earthen Ring Farseer in 96.5% of aggro-hunter elites. No comparison with human or meta decks.
  - Source: [arXiv 1904.10656 / ar5iv](https://ar5iv.arxiv.org/html/1904.10656), [venue/code](https://github.com/tehqin/EvoSabber)
- **Zhang, Fontaine, Hoover, Nikolaidis, "Deep Surrogate Assisted MAP-Elites for Automated Hearthstone Deckbuilding" (DSA-ME), GECCO 2022.**
  - Surrogate: an online MLP (128-32-16, ELU) on a bag-of-cards vector (copies 0/1/2 of each of 180 cards). It predicts the objective and the behaviour measures and pre-screens candidates for MAP-Elites.
  - Behaviour descriptors: average turns per game (aggro to control) and average hand size.
  - Budget: 10,000 ground-truth evaluations × 200 games against 6 opponent decks.
  - Results: QD-score 338.5±5.9 vs 136.9±2.0 for plain MAP-Elites, max win 98.4% vs 90.6%, cells filled 31.9% vs 14.4%. The surrogate predicted the measures much better than the objective (MSE 0.44 turns, 0.07 hand size, 14.7 health difference).
  - Decks were played by one fixed 109-parameter neural heuristic trained on Miracle Rogue, so agent dependence was not measured.
  - Source: [ar5iv 2112.03534](https://ar5iv.labs.arxiv.org/html/2112.03534)
- **García-Sánchez, Tonda, Mora, Squillero, Merelo, "Automated Playtesting in Collectible Card Games using Evolutionary Algorithms: a Case Study in HearthStone", Knowledge-Based Systems 2018.** This extends their CIG 2016 "Evolutionary deckbuilding in Hearthstone".
  - Fitness: a (μ+λ) EA with fitness = wins against 8 human meta decks, 16 games each (128 games per evaluation), played by MetaStone's Greedy-Optimize-Turn AI. That was the best of 4 built-in AIs, winning 37.5% of an 11,520-game round robin.
  - Smart Mutation: swaps a card only for one of similar mana cost, to preserve the mana curve. It "deliver[ed] better decks in the majority of reported experiments."
  - Results: evolved decks beat the human decks in all 9 classes, e.g. 82.8% / 81.3% (no smart / smart mutation) vs 71.1% for the best human deck, and 60.9% / 67.2% vs 32.4% for the worst. The standard deviation of win rates across decks fell from 14.57 (human) to 7.44 / 5.83.
  - Source: [author manuscript](https://iris.polito.it/bitstream/11583/2706329/1/2018-kbsys.pdf)
- **Bhatt, Lee, de Mesentier Silva, Watson, Togelius, Hoover, "Exploring the Hearthstone deck space", FDG 2018.**
  - Evolution strategies produced decks that "convincingly beat" the game's built-in decks and did reasonably well against decks they had not been evolved against.
  - A second round evolved against the first round's decks. The authors read this as some transitivity of the deck space.
  - Source: [NJIT record](https://digitalcommons.njit.edu/fac_pubs/8454)
- **Chen, Amato, Nguyen, Cooper, Sun, Seif El-Nasr, "Q-DeckRec", CIG 2018.**
  - Formulation: deck building as an MDP. The state is (own deck, opponent deck, step); an action swaps one card in or out; an episode is 15 swaps from a random deck. The reward is exp(10·win rate), with win rate from 300 MetaStone games at about 5 s per call and about 5% standard deviation. Q-learning uses an MLP.
  - Results: after 3 days of training it reaches 0.93 win rate in 9.63 CPU-seconds per new problem. A GA needs 15.9 CPU-hours for 0.94, about 6,000× more at solve time (training excluded).
  - A random-sampling baseline scored by a learned predictor peaked at 0.84 and then degraded with more samples, because outlier decks fooled the predictor.
  - Source: [ar5iv 1806.09771](https://ar5iv.labs.arxiv.org/html/1806.09771), [PDF](https://web.cs.ucla.edu/~yzsun/papers/2018_cig_deckrec.pdf)
- **Kowalski & Miernik, "Evolutionary Approach to Collectible Card Game Arena Deckbuilding using Active Genes" (LOCM), arXiv 2001.01326, 2020.**
  - Active genes: only the genes for cards in the current draft are varied, and the merged individual blends parent and child (best variant 0.75 parent / 0.25 child).
  - Results with a greedy player: AG_weights 57.28% vs 52.16% for a plain EA and 47.92% / 47.19% for the contest drafts. With a random player all methods sit at about 49-52%, which the authors attribute to noise.
  - Budget: 10^6 games. The plain EA generalised worse from training drafts to unseen drafts.
  - Source: [ar5iv 2001.01326](https://ar5iv.labs.arxiv.org/html/2001.01326)
- **Vieira, Tavares, Chaimowicz, "Drafting in Collectible Card Games via Reinforcement Learning", SBGames 2020 (best paper).** There is a journal version in Entertainment Computing 2022.
  - Setup: PPO draft policies (30k self-play episodes) for LOCM, each trained with one fixed battle agent (max-attack or a greedy 1-ply heuristic).
  - Results: up to 83.5% vs the original max-attack drafter. Swapping the learned drafter into max-attack moved it from 10th (34.0%) to 4th (46.1%) in a re-run of the CoG 2019 tournament. Some opponents did better against the new version, which the authors read as non-transitivity.
  - The "Immediate" drafter, which ignores previously picked cards, beat the history-aware and LSTM drafters. The authors' explanations: too few episodes, or battle agents too weak to exploit synergies.
  - The authors recommend "a reward model that reflects the average win rate against a pool of diverse opponents, instead of just one."
  - Source: [SBGames 2020 PDF](https://www.sbgames.org/proceedings2020/ComputacaoFull/209690.pdf)
- **LOCM competition context.** The top 2019 agents (Coac, closet-ai, icebox) drafted from precomputed fixed card rankings. Coac won the re-run CoG 2019 tournament at 90.3% using that fixed ranking plus search in battle. — [Vieira et al. 2020](https://www.sbgames.org/proceedings2020/ComputacaoFull/209690.pdf); competition overview: Kowalski & Miernik, "Summarizing Strategy Card Game AI Competition", CoG 2023, [arXiv 2305.11814](https://arxiv.org/abs/2305.11814)
- **Magic: The Gathering drafting is almost entirely supervised imitation of human picks.**
  - Ward et al., "AI solutions for drafting in Magic: the Gathering" (CoG 2021): over 100,000 human drafts from Draftsim; a deep network beat the other bots. — [arXiv 2009.00655](https://api.deepai.org/publication/ai-solutions-for-drafting-in-magic-the-gathering)
  - Bertram, Fürnkranz, Müller (CoG 2024), generalised card representations: reportedly predicts 55% of human choices on completely unseen cards. This figure is from a search summary and was not checked in the full text. — [PDF](https://webdocs.cs.ualberta.ca/~mmueller/ps/2024/COG24_Magic_Drafting.pdf), [arXiv 2407.05879](https://arxiv.org/html/2407.05879v1)
  - Community 17lands-trained models report about 91% agreement with human picks (ANA, self-reported). — [Hugging Face](https://huggingface.co/alakazamworld/ana-mtg)
- **Genetic-algorithm deck building for Magic** exists as a 2017 NTNU master's thesis assessed by an expert. An anecdotal blog reports a GA deck going 0-7 at a February 2018 Dutch Standard Open. — [NTNU](https://ntnuopen.ntnu.no/ntnu-xmlui/handle/11250/2462429), [Hackernoon](https://hackernoon.com/machine-learning-magic-64a6a7f864d4)

### Inferences
- **F1, F3: replace the single population with a quality-diversity archive.** Single-population fitness selection is the setting in which the literature reports convergence to one archetype. Vieira et al. describe "the common outcome of evolutionary algorithms of converging to a single deck archetype", which MAP-Elites prevents.
  - Concrete change: replace the 99-deck population plus turnover with a MAP-Elites archive whose descriptors are generic and computed from play, e.g. average game length (as in DSA-ME) and average hand size or a cards-played-per-turn statistic. Use sliding (percentile) boundaries so the archive does not pile into the wall region.
  - Each cell keeps its own elite, so walls cannot take over cells defined by short games. The project's type cap is a crude, hand-chosen version of this.
- **F3: pre-screen candidate edits with a cheap online surrogate.** Selection running at the noise floor is the regime DSA-ME and Q-DeckRec address.
  - Concrete change: an online bag-of-cards surrogate (60 counts → predicted win rate against the archive), retrained every iteration on all evaluated decks. Use it to pre-screen candidate edits and spend real games only on the top-k.
  - Q-DeckRec warns that the surrogate can be fooled by outlier decks, so keep ground-truth confirmation.
- **F3: a structure-preserving mutation operator.** García-Sánchez's Smart Mutation (swap within the same cost band) is a generic version of the project's per-card edits.
  - The game-agnostic analogue is "swap within the same card supertype or cost band" (Energy for Energy, Trainer for Trainer, Basic for Basic). It changes card choices without drifting the composition, so composition can only move through deliberate type-changing edits that have to pass a stricter test.
  - This is my inference. It also partly bakes in the initial ratio, so it should be one operator among several.
- The Vieira "Immediate" result suggests that small or simple draft learners with weak pilots learn card-quality rankings, not synergies. This is consistent with F3's head collapse onto a ranking of incumbent cards (inference).

### Gaps
- I found no paper called "EvoDeck". I found no published RL drafting system for the Pokemon TCG (see the Pokemon section).
- I found no paper that builds 60-card constructed decks by RL from scratch, other than the ByteDance Hearthstone work below.
- The Bertram 2024 figures and the journal version of Vieira 2022 were not read in full.

## Joint learning of deck building and play (Xi/Xiao et al. 2023 LOCM and Hearthstone) and how they avoid collapse

### Takeaway
The only strong from-scratch systems that learn deck building and play together (ByteDance's ByteRL for LOCM and Hearthstone) use four things:
- one network whose draft and battle heads are trained end-to-end on whole-game trajectories;
- fictitious play against a payoff-weighted pool of historical policies;
- no discounting (γ=1);
- in Hearthstone, forced random picks at the start of deck construction during training ("random-CB"), which the authors say made the decks more human-like.

Neither paper reports a deck-diversity metric or an explicit anti-collapse mechanism, and the from-scratch Hearthstone agent visibly over-used healing cards.

### Cited Findings
- **Xi, Zhang, Xiao, Huang, Deng, Liang, Chen, Sun (ByteDance), "Mastering Strategy Card Game (Legends of Code and Magic) via End-to-End Policy and Optimistic Smooth Fictitious Play", arXiv 2303.04096, 2023.**
  - End-to-end vs alternating training: one network outputs the deck-building policy, the battle policy and the value, and a full game (draft plus battle) is one trajectory. Alternating training of the two stages was worse, because it "artificially isolates the two stages, which hinders training-signal transfer". On LOCM 1.5, end-to-end scored 65.5% vs the Evo-AT baseline; Neural-AT scored 56.5%.
  - OSFP opponent sampling:
    - With probability p=0.6 the opponent is the current learner; otherwise it is sampled from a historical pool by a function of each entry's win/game counts.
    - The learner joins the pool when its win rate against every historical policy exceeds ξ=0.7, or after c=6 failed checks.
    - The latest iterate gets mixing weight 2, older ones 1 ("optimistic"), which gives last-iterate convergence.
    - The regulariser is negative entropy per information state.
  - Results: won both COG2022 tracks, with average win rates of 84.41% (LOCM 1.5) and 94.56% (LOCM 1.2) against all other submissions. Head-to-head it beat the runner-up NeteaseOPD 63%.
  - Compute: 24 "units" (1 V100 + 600 CPU cores each) for about 72 h at about 500K frames per second.
  - The paper does not discuss deck diversity or collapse.
  - Source: [ar5iv 2303.04096](https://ar5iv.labs.arxiv.org/html/2303.04096)
- **Xiao, Zhang, Huang, Huang, Chen, Sun (ByteDance), "Mastering Strategy Card Game (Hearthstone) with Improved Techniques", CoG 2023 (arXiv 2303.05197).** Source for all items below: [arXiv 2303.05197](https://arxiv.org/pdf/2303.05197)
  - Random-CB: before each training match, each player draws n∈{0,1,2,4} with probabilities (0.5, 0.25, 0.125, 0.125), and the first n deck-building picks are uniformly random. This is disabled at evaluation. "Intuitively, a diversified deck helps the learning of BT [battle] policy… We find the model is more prone to build a 'human-like' deck with random-CB." One learned Mage deck resembled "Flamewaker Mage", a popular human deck from April 2015. Win rate was on par, but the authors "regard it as progress."
  - γ=1.0 instead of 0.99, because episodes have at most about 100 steps and reward is only terminal ±1: about +7% win rate.
  - Halving the actors to reduce off-policyness: +10.0%.
  - Revised V-trace clipping and a PPO-style loss: +15.1%.
  - Separate models per hero: +6.5%.
  - "Cheat" model that sees n of the opponent's deck picks (asymmetric during training): +5.5%. The authors say it "encourages diversity" and produces adversarial, opponent-specific decks.
  - Final model: 73.6% vs the LOCM-champion baseline algorithm. It won all four Bo5 Conquest tournaments against a streamer whose best rank was top 10 in China (3:0, 3:0, 3:1, 3:2), after 23 days of training on 24 V100s and 5,856 CPU cores.
  - Human tester: "AI takes so many healbots. It's almost killed and two healbots heal it!" A 16-day model also wasted Antique Healbot at full health.
  - Hero (class) is sampled uniformly, so decks are spread across 9 class card pools by construction.
- **Exploitability of the end-to-end/OSFP agent.** Haluska & Schmid, "Learning to Beat ByteRL: Exploitability of Collectible Card Game Agents" (arXiv 2404.16689, 2024), find ByteRL's LOCM play "highly exploitable". — [arXiv](https://arxiv.org/abs/2404.16689)
  - Rubin (Georgia Tech), arXiv 2609.06816 (Sep 2026), replicated the attack: a PPO best response reaches 90% against ByteRL within 50 iterations, and adding decision-time search cuts converged exploitability by 21-28 points. — [arXiv 2609.06816](https://arxiv.org/pdf/2609.06816)

### Inferences
- **F1, F2, F5: random-CB is the cheapest transferable idea here.** It is a partial version of the project's "practice games between random decks", applied to the drafted decks themselves.
  - Concrete change: in pilot-training games, replace a geometrically distributed number of the population deck's cards (0 with p=0.5, 1-4 otherwise, scaled to 60 cards, e.g. 0/2/4/8) with random legal cards, and never do this at evaluation.
  - This keeps the pilot exposed to near-population decks containing cards the population has dropped (Trainers). That attacks the loop "pilot cannot use Trainers, so drafts drop Trainers, so pilot never learns Trainers". It is a direct, published lever toward human-like decks.
- **F4, F1: check the pilot's γ (and GAE λ). Strong hypothesis, not established.**
  - With terminal ±1 rewards, γ<1 makes a loss at step T worth −γ^T. A 0.99-discounted pilot values losing at step 300 at about −0.05, against about −0.37 at step 100.
  - So a discounted pilot is paid to delay losses: stall, heal, remove Energy, win by deck-out. That is exactly the wall style.
  - ByteDance found γ=1.0 better by about 7% in Hearthstone. DeNA's Pokemon TCG Pocket AI also dropped discounting for non-state-changing steps (next section).
  - This is my inference from the reward arithmetic. It holds only if the pilot uses γ<1 over many decision steps per game, and is worth checking first because the change is trivial.
- **F3: train draft and play end-to-end instead of by accept/reject.** End-to-end beat alternating training (65.5% vs 56.5%).
  - The project's draft heads read the pilot encoder but are trained by REINFORCE on whether edits score better. The end-to-end alternative backpropagates game outcomes into the draft head with the pilot's value as baseline, using every game rather than only selection contests. That removes the noise-floor accept/reject step.
  - ByteDance still needed a fictitious-play pool (p=0.6 self, 0.4 historical, payoff-weighted sampling, add-to-pool at 70%) to keep training stable.
- **F2: payoff-weighted historical pool for the pilot-and-deck agent.** OSFP's pool admission rule (beat all historical policies at 70%) and payoff-weighted sampling make a cheap league for both components. For F2 it means the pilot keeps training against historical pilot-and-deck pairs, which are more varied, not only the current population.
- **F1 parallel.** The Hearthstone "so many healbots" comment echoes F1 (healing Energy, walls), even at master level. The healing bias of from-scratch self-play may be general, not specific to the project's pipeline (inference from one anecdote).
- **Compute caveat.** These results used about 10^3 times the project's compute (24 V100 + about 6k CPU cores for weeks), so the project cannot expect the same amount of implicit diversity from long training.

### Gaps
- Neither ByteDance paper gives a deck-diversity measure, a deck-type distribution over training, or what fraction of decks resembled human archetypes. "Human-like" rests on one anecdote and a comparison figure.
- The exact form of the OSFP sampling function f is not given.
- The full Haluska & Schmid exploitability numbers were not read; only Rubin's replication figure (90% within 50 iterations) was seen.

## Automated playtesting and balance: evidence that deck or strategy evaluation depends on agent skill, and remedies

### Takeaway
The literature consistently finds that decks optimised under a given agent are optimal for that agent's play style. The standard remedies are evaluation by several agents or skill levels, a diverse opponent pool, and search-based or more human-like evaluators. None of the papers quantifies how deck rankings shift as a learned pilot gets stronger.
- García-Sánchez et al.: evolved decks beat human meta decks across all classes when played by a greedy AI, but were all aggro, because the AI rarely trades.
- Fontaine et al. state their method "is dependent on a particular game-playing agent".

### Cited Findings
- **García-Sánchez et al. 2018 (KBS).** Source for all items below: [manuscript](https://iris.polito.it/bitstream/11583/2706329/1/2018-kbsys.pdf)
  - "Constraining the evolution to evaluating fights against a specific AI has the risk of overfitting to the particular AI's play style."
  - MetaStone's AI "plays pretty aggressively, rarely trading… It is thus not surprising that basically all evolved decks can be classified as Aggro or Mid-Range, with mana curves unbalanced towards cheap, cost-effective cards."
  - Fel Reaver (an 8/8 for 5 that mills you whenever the opponent plays a card) recurred because "MetaStone cannot deal with Fel Reaver… it kept playing as usual, without exploiting this big minion's weakness."
  - In the 11,520-game round robin of human decks under all 4 AIs, aggressive decks won most regardless of AI, but "the other types of decks also benefit from using the Greedy methods."
- **Fontaine et al. 2019 (GECCO).**
  - The methodology "is dependent on a particular game-playing agent." Aggro-strategy decks favoured low average mana cost, while control decks did well across mana curves.
  - The aggro hunter lost to all other combinations even though its mana curve resembled the control hunter's.
  - Agent bias is acknowledged but not tested.
  - Source: [ar5iv 1904.10656](https://ar5iv.arxiv.org/html/1904.10656)
- **Zook, Harrison, Riedl, "Monte-Carlo Tree Search for Simulation-based Strategy Analysis" (FDG 2015; arXiv 2019).** Source: [arXiv 1908.01423](https://arxiv.org/abs/1908.01423), [FDG PDF](https://faculty.cc.gatech.edu/~riedl/pubs/zook-fdg15.pdf)
  - Skill is modelled by the MCTS rollout budget: enough rollouts to see 1 move ahead (weak) or 2 moves (strong). In Cardonomicon the budgets were 100 / 2,500 / 5,000 rollouts.
  - Card game Cardonomicon: stronger agents used three cards "with large amounts of health but low attack for their cost" disproportionately more than weaker agents, to trade into several weaker cards over multiple turns.
  - Scrabble: the skill gap narrows as both agents get stronger. Games shorten from 26 turns (weak vs weak) to 22 (strong vs strong).
- **Mahlmann, Togelius, Yannakakis, "Evolving Card Sets Towards Balancing Dominion", IEEE CEC 2012.** Card sets were evaluated with three agents of different skill. The key result was that certain cards gave balanced games regardless of skill or behaviour. This is from the abstract only. — [ITU record](https://pure.itu.dk/en/publications/evolving-card-sets-towards-balancing-dominion/), [PDF](https://um.edu.mt/library/oar/bitstream/123456789/22933/1/Evolving_card_sets_towards_balancing_dominion.pdf)
- **de Mesentier Silva, Canaan, Lee, Fontaine, Togelius, Hoover, "Evolving the Hearthstone Meta", CoG 2019.** Matchup win rates between decks "played by different strategies" before and after card changes, with an EA searching card-attribute changes that move deck win rates toward 50%, plus a multi-objective variant that minimises the number of changes. The full text was not read. — [arXiv 1907.01623](https://arxiv.org/abs/1907.01623)
- **Q-DeckRec (2018).** The authors flag that their evaluation proxy "is only based on a greedy heuristic rather than trained on human play traces", so win rates may not transfer. They excluded tree-search proxies as too slow. — [ar5iv 1806.09771](https://ar5iv.labs.arxiv.org/html/1806.09771)
- **Vieira et al. 2020.** Drafters are evaluated with the battle agent they were trained with. The authors note that literature drafters "were created to work with a specific battle agent" and that retraining for each is "prohibitive". — [PDF](https://www.sbgames.org/proceedings2020/ComputacaoFull/209690.pdf)
- **Search as a stronger and less exploitable evaluator (Rubin 2026, LOCM).** Source: [arXiv 2609.06816](https://arxiv.org/pdf/2609.06816)
  - Search: beam search over full-turn plans scored by a value net, with determinised opponent hands and decks ("worlds").
  - Raw strength: the same network scores 26.8% vs ByteRL as argmax policy and 51.35% [50.37, 52.33] with search (10,000 pre-registered games), so search is worth +24.6 points.
  - Ablations:
    - plan beam width 12 to 96 keeps helping;
    - more than 32 worlds does not;
    - "More depth does not increase agent quality. Most of the value of the search is immediately gained by evaluating plans."
  - Knowing the opponent's exact list: 59.6% vs 50.5% with a uniform prior.
  - Exploitability and imitation:
    - Search cut converged best-response exploitability by 21-28 points.
    - Imitation fidelity "does not directly translate to playing strength", and quadrupling imitation data gave +8 points.
- **De Mesentier Silva, Borovikov, Kolen, Aghdaie, Zaman, "Exploring Gameplay With AI Agents" (AIIDE 2018)** is an industry example (The Sims Mobile) of simulation agents exposing action imbalances. It does not address skill dependence. — [arXiv 1811.06962](https://arxiv.org/abs/1811.06962)

### Inferences
- **F2: the García-Sánchez result reproduces the project's finding.** Their human decks played by MetaStone AI lost to agent-tuned evolved decks (e.g. 71.1% vs 82.8%), just as walls under their own pilot beat human lists 0.72-0.76 but drop to 0.23-0.24 under an older generalist pilot. The literature treats this as overfitting to the evaluator's play style and expects composition to skew toward what that agent plays well (aggro for greedy MetaStone, walls for the project's pilot).
- **F2 remedy: score deck fitness with an ensemble of pilots, not only the co-trained one.** Score each candidate edit by the minimum, or a low quantile, of its win rate over evaluators, e.g. the current pilot, a frozen older generalist, and a pilot with one-turn plan search.
  - A deck survives only if it wins regardless of who pilots it. This operationalises Mahlmann's "balanced regardless of skill" criterion and Vieira's "pool of diverse opponents" recommendation (inference).
- **F2, F4: use search as the evaluator, not as a distillation target.** Rubin's ablation says most of the value comes from evaluating complete one-turn plans with the value net, with depth adding nothing. This matches the project's finding that one-turn search on the human side wins the prize race.
  - Since distilling search into the policy failed three times, use the cheap one-turn-plan search pilot only for the selection/evaluation games of the drafting loop. Deck fitness is then measured under the stronger, less exploitable player, which the literature suggests reduces evaluator bias (inference).
- **Caution from Zook et al.** A stronger player can legitimately value high-health, low-attack cards more. That walls rise with pilot skill is not by itself proof of a bug; the human-list ground truth is what flags it.
- **F2 diagnostic: train a short best-response pilot against the walls.** Train a short PPO best-response pilot (about 50 iterations, as in Haluska & Schmid / Rubin) against the wall population's pilot-and-deck pairs. If walls are a co-adaptation artefact, a cheap exploiter should find a high-win-rate counter quickly, and that counter-deck or pilot can be injected into the league. This needs no human data (inference).

### Gaps
- I found no study that holds decks fixed and measures how CCG deck rankings change as an RL-trained pilot improves; Zook covers only MCTS budget and gameplay statistics.
- The Fontaine/Hoover-line paper the task calls "agent skill and game balance" was not found under that title; the closest are Fontaine 2019's agent-dependence caveat, Zook et al., and Mahlmann et al.
- de Mesentier Silva et al.'s Ticket to Ride agent-based playtesting work (FDG 2017) was not retrieved.

## Has any work rediscovered a human metagame from scratch, and how was it validated?

### Takeaway
No. The best evidence is qualitative: ByteDance's from-scratch Hearthstone agent built a Mage deck that a top human recognised as "Flamewaker Mage", a 2015 meta deck. Evolutionary Hearthstone studies found individual human staple cards, with validation by expert inspection. No paper measures distributional agreement between a learned metagame and a human metagame.

### Cited Findings
- Xiao et al. 2023 (Hearthstone): "there is no prior domain knowledge or expert data during the training process… but the human player regards the AI's deck as Flamewaker Mage which is a popular choice in the Hearthstone community." The appendix shows the AI deck next to the human deck. Random-CB was credited with making human-like decks more likely. Validation: a top-10 (China) player's judgement and Bo5 wins. — [arXiv 2303.05197](https://arxiv.org/pdf/2303.05197)
- García-Sánchez et al. 2018:
  - Evolved decks "feature several strong cards frequently chosen by human players". The evolved Rogue reused Gadgetzan Auctioneer and Questing Adventurer from the human Oil Rogue.
  - Dr. Boom recurred and was "later identified by an expert as unbalanced". Fel Reaver recurred because of agent blindness.
  - Validation: one author's expert inspection (a rank-10-level player with over 13,000 games).
  - Source: [manuscript](https://iris.polito.it/bitstream/11583/2706329/1/2018-kbsys.pdf)
- Fontaine et al. 2019 made no comparison with human or meta decks. — [ar5iv](https://ar5iv.arxiv.org/html/1904.10656)
- Bhatt et al. 2018 compared against the game's built-in decks, not a human meta. — [NJIT](https://digitalcommons.njit.edu/fac_pubs/8454)

### Inferences
- The project's validation (composition statistics of 24 human tournament lists, plus head-to-head with human lists under several pilots) is already more quantitative than anything published for CCGs. The validation design is novel; there is no benchmark to copy.
- A literature-consistent validation would add three checks (inference):
  - card-overlap or archetype similarity to the human lists;
  - a pilot-independent strength test, e.g. the min over pilots including a search pilot;
  - the exploitability of the discovered meta.

### Gaps
- I found no work, in CCGs or Pokemon team building, that reports reproducing the composition statistics or archetype distribution of a human tournament meta from self-play.

## Pokemon-specific AI (Pokemon TCG, TCG Pocket, VGC/Showdown team building) relevant to F1-F5

### Takeaway
No published RL deck builder exists for the paper Pokemon TCG.
- DeNA's TCG Pocket battle AI (an industry talk) trains on procedurally generated decks: evolution lines are kept together, Energy needs are respected, and complex or high-Energy cards are deliberately oversampled so the pilot learns to use them. It also drops discounting on non-state-changing steps.
- VGC-Bench (AAMAS 2026) shows the generalist-vs-specialist trade-off of F2: training on more teams lowers in-distribution strength and raises exploitability, but improves generalisation to unseen teams.

### Cited Findings
- **DeNA (with The Pokemon Company and Creatures), Pokemon TCG Pocket battle AI, CEDEC 2026 talk by Kosuke Sakimi, reported by Inven Global.** Source for all items below: [Inven Global](https://www.invenglobal.com/articles/24133/how-reinforcement-learning-ai-tackles-the-complex-rules-of-pok%C3%A9mon-trading-card-game-pocket)
  - Model and training: HandyRL; a stateless Transformer of about 2M parameters; 50M episodes per model at about 1 s per episode, on six cloud machines.
  - Deck generation:
    - Basic Pokemon are grouped with their evolutions as one unit, and Energy requirements are adjusted.
    - Scores make complex or high-Energy cards appear more often "so the AI would learn to use them"; decks are filled by score-weighted random draws.
    - Synergy cards enter only with their parent (e.g. Rookie Researcher only if Mew ex is present).
  - Problems and fixes:
    - The AI played Speed Up without retreating. Fix: raise Speed Up's deck-inclusion rate, add a feature showing whether retreat cost was reduced, and add a targeted penalty. Correct use reached 96.2%.
    - A direct negative reward for Windie ex's self-damage made the AI treat Windie ex's presence as bad overall. Fix: a penalty only on the self-damaging action.
    - No win rates were reported.
- **PTCG-Bench (arXiv 2605.29653, May 2026)** benchmarks LLM agents on the Pokemon TCG. Agents reach "non-trivial gameplay performance", but "sustained and stable self-evolution remains challenging"; results are sensitive to harness design. It is about play, not deck building. — [arXiv](https://arxiv.org/abs/2605.29653)
- **Angliss, Cui, Hu, Rahman, Stone, "VGC-Bench: Towards Mastering Diverse Team Strategies in Competitive Pokemon", AAMAS 2026 (arXiv 2506.10326).** Source: [arXiv](https://arxiv.org/abs/2506.10326)
  - Team space is about 10^139.
  - Baselines: heuristics, LLM agents, behaviour cloning, and self-play, fictitious play and double oracle.
  - In single-team mirror matches the agents can beat a professional VGC player. As the number of training teams grows, the best single-team method "performs worse and is more exploitable, but has improved generalization to unseen teams."
- **VGC AI Competition (IEEE CoG).** Agents must both battle and "decide the strongest team against the current Meta" on randomly generated rosters. A related FEUP "meta-game balance" ecosystem pits team builders, who narrow toward optimal Pokemon, against balancer agents that try to maximise the number of Pokemon selected. — [CoG 2025 VGC](https://cog2025.inesc-id.pt/vgc/), [FEUP page](https://dei.fe.up.pt/dev/?p=12851)
- **García-Sánchez et al. 2018** explicitly propose their method for "a 6 Pokemon team… pairing evolved Pokemon teams against the best ones in championships." — [manuscript](https://iris.polito.it/bitstream/11583/2706329/1/2018-kbsys.pdf)

### Inferences
- **F5, F1: practice-deck generator.** DeNA's generator is a heavier, curated version of the project's random practice decks. The generic, rules-derived parts carry to other games and do not encode strategy:
  - keep prerequisite chains intact (evolution "evolves from" links, cards whose text references another card);
  - oversample cards that are rarely drafted or rarely played, so the pilot gets experience with them.

  An "Energy requirements adjusted" rule would be a game-specific prior and should be avoided under the project's constraints. The F5 failure (Pokemon piles that win by deck-out) is what one expects if practice decks rarely contain playable Trainer and evolution packages, so the pilot never learns their value (inference).
- **F2: DeNA's reward lesson.** A direct penalty on a card's outcome made the agent treat the card's mere presence as bad. The same could happen in the project's draft heads if deck-level rewards are noisy: a card that appears in losing decks gets marked bad regardless of how it was played (inference).
- **F2: VGC-Bench's trade-off is the same as the project's.** Specialist pilots are stronger in-distribution but exploitable; generalists transfer. The project's "varied population keeps the pilot general" result has external support. The remedy direction is to keep training-distribution diversity, through archives and random-CB, rather than to anchor the policy.

### Gaps
- I found no peer-reviewed RL or evolutionary deck-building work for the paper Pokemon TCG (any format).
- The DeNA work is known only through a press report of a conference talk, with no win rates or decklist statistics.
- Showdown battle bots (e.g. PokéChamp, Metamon) were not reviewed here; they concern battling with fixed or human-data teams.

## Mapping to F1-F6: concrete changes to the loop suggested by the literature

### Takeaway
Ranked by literature support per unit of compute on one desktop:
1. Check and remove reward discounting.
2. Random-CB-style partial random decks in pilot training.
3. Score deck fitness by the minimum over several pilots, including a one-turn plan-search pilot used only for evaluation.
4. A MAP-Elites archive with play-derived, generic descriptors and sliding boundaries in place of the single population.
5. An online bag-of-cards surrogate to screen edits.
6. A fictitious-play pool (OSFP-style) for pilot opponents.
7. A short best-response exploiter as a diagnostic.

### Cited Findings
- **F4, F1: γ=1.0.** +7% in Hearthstone with terminal-only rewards. — [Xiao et al. 2023](https://arxiv.org/pdf/2303.05197); DeNA also removed discounting on non-updating steps — [Inven Global](https://www.invenglobal.com/articles/24133/how-reinforcement-learning-ai-tackles-the-complex-rules-of-pok%C3%A9mon-trading-card-game-pocket)
- **F1, F2, F5: random-CB.** n∈{0,1,2,4} random initial picks with probabilities (0.5, 0.25, 0.125, 0.125), training only; produced more "human-like" decks. — [Xiao et al. 2023](https://arxiv.org/pdf/2303.05197)
- **F2: evaluator choice drives deck composition.** Greedy AI led to aggro decks and agent-blind card picks. — [García-Sánchez et al. 2018](https://iris.polito.it/bitstream/11583/2706329/1/2018-kbsys.pdf); use diverse opponents or agents — [Vieira et al. 2020](https://www.sbgames.org/proceedings2020/ComputacaoFull/209690.pdf), [Mahlmann et al. 2012](https://pure.itu.dk/en/publications/evolving-card-sets-towards-balancing-dominion/)
- **F4, F2: one-turn plan search with a value net.** +24.6 points; depth adds nothing; it is less exploitable. — [Rubin 2026](https://arxiv.org/pdf/2609.06816)
- **F1, F3: MAP-Elites with sliding boundaries keeps diverse elites.** DSA-ME doubles QD-score and cell coverage with a bag-of-cards surrogate, using generic descriptors (turns per game, hand size). — [Fontaine et al. 2019](https://ar5iv.arxiv.org/html/1904.10656), [Zhang et al. 2022](https://ar5iv.labs.arxiv.org/html/2112.03534)
- **F3: end-to-end draft-and-battle gradients beat alternating training** (65.5% vs 56.5%). — [Xi et al. 2023](https://ar5iv.labs.arxiv.org/html/2303.04096)
- **F2, F3: OSFP pool.** Self-play with p=0.6, otherwise payoff-weighted historical opponents; add to the pool when beating all at 70%. — [Xi et al. 2023](https://ar5iv.labs.arxiv.org/html/2303.04096)
- **F2: self-play CCG agents are highly exploitable.** A best response reaches 90% in 50 PPO iterations. — [Rubin 2026](https://arxiv.org/pdf/2609.06816), [Haluska & Schmid 2024](https://arxiv.org/abs/2404.16689)
- **F3: noisy fitness.** Smaller, batched updates over active genes and parent-weighted merging (0.75/0.25) beat plain EAs under noise (57.3% vs 52.2%). — [Kowalski & Miernik 2020](https://ar5iv.labs.arxiv.org/html/2001.01326)

### Inferences
1. **(F4, F1) Pilot discount.** If the pilot uses γ<1 (or λ<1 with a biased critic) over hundreds of decisions per game, it is rewarded for delaying losses. That favours stalling, healing, Energy removal and deck-out, i.e. walls.
   - Test: retrain or fine-tune the pilot with γ=1 (keep λ for variance), then re-measure the walls vs human-lists gap and the median game length.
   - This is the cheapest test with a mechanism that predicts F1 and F4 together. It is my inference and must be checked against the project's actual γ.
2. **(F1, F2, F5) Random-CB in pilot training.** Replace a small random number of cards in population decks with random legal cards, in training games only. This complements the separate practice games: the pilot sees off-distribution cards inside on-distribution shells.
3. **(F2) Min-over-pilots fitness.** Each candidate edit's score is the minimum (or 25th percentile) of its win rate under the current pilot, a frozen generalist, and a search-augmented pilot. This directly penalises decks that only win with their co-adapted pilot, which the project measured at 0.72-0.76 vs 0.23-0.24.
4. **(F4) Search for evaluation, not distillation.** Use the one-turn plan search only in the evaluation games that decide deck moves. Rubin's ablation suggests plan breadth matters more than depth, so a small beam of whole-turn plans may suffice. The cost is limited to the selection games.
5. **(F1, F3) Archive instead of population.** MAP-Elites cells over two play-derived generic descriptors, e.g. median game length and mean cards played per turn, or the fraction of games won by deck-out vs prizes. Use percentile (sliding) boundaries and keep turnover inside cells.
   - It is a generalised, game-agnostic type cap. The walls can occupy only the long-game/deck-out cells.
   - The draft heads can be conditioned on the target cell, which acts as exploiter diversity, and compete only within it. That avoids the earlier failure where exploiter heads drifted to the main type.
6. **(F3) Surrogate-screened edits.** An online bag-of-cards MLP predicts each edit's win rate against the archive. Spend games only on the surrogate's top candidates and accept a move only on a significant win-rate gain in confirmation games.
7. **(F2, F3) OSFP-style league for the pilot.** Keep a pool of past (pilot, deck) snapshots, sample them by payoff (harder ones more often), and admit a new snapshot only when it beats all of them at 70% or more. This restores opponent diversity without human data.
8. **(F2 diagnostic) Short PPO best-response pilot** trained against the wall population (no human data). If it reaches a high win rate quickly, the walls are an exploitable co-adaptation; add the exploiter's decks and pilot to the league.
9. **(F6)** No paper found here addresses turn-limit draws. Xiao et al. used complete games of at most about 100 steps with γ=1, so the literature leans toward full games plus undiscounted terminal reward rather than truncation (inference).

### Gaps
- None of the cited systems ran on a single desktop GPU at the project's scale, except Vieira (30-min to 3-h drafter training with scripted battlers) and the EA studies, which ran on CPU clusters. Compute transfer is uncertain.
- No paper tests min-over-evaluators deck fitness or archive-plus-RL-pilot co-training directly; points 3 and 5 are syntheses, not reported results.
