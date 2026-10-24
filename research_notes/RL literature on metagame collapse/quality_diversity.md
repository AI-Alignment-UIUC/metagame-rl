# Quality-diversity and open-ended search against convergence to one deck type

Scope: what quality-diversity (QD) and open-endedness methods offer against convergence to one solution, especially for discrete designs such as decks, and how they combine with RL policies. Failure modes F1-F6 are the ones in the task brief. Tags such as [F1] mark which failure mode a finding bears on. A "Loop change:" line is my proposal, not a claim from the source.

Prior attempts in this repo: progress-log #27 (2026-10-05) dropped MAP-Elites, the RL-trained edit policy, rectified Nash and exploiter episodes from the builder plan "unless plain search stalls". It kept "a minimum distance of ~10 cards for a new population deck" ([progress-log #27](file:///C:/Users/evanc/Desktop/333/metagame-rl/notes/progress-log.md)). A grep of `notes/` and `README.md` for MAP-Elites, novelty, niching, fitness sharing, speciation and crowding found no later QD experiment. QD has been proposed but never run here.

## 1. MAP-Elites and its variants, novelty search with local competition, and descriptors learned without domain knowledge

### Takeaway
MAP-Elites-style methods keep diversity structurally: each solution competes only with others that have a similar behaviour descriptor. The descriptor decides which kinds of diversity survive. Some descriptors need no domain knowledge: AURORA's learned encoder, and Enhanced POET's PATA-EC, which describes an item by how a panel of other agents ranks on it. The PATA-EC version, a deck described by its rank-normalised matchup profile against a panel, is the most direct fit for decks without adding a human prior.

### Cited findings
- **MAP-Elites with sliding boundaries (MESB), Hearthstone decks.** Fontaine, Lee, Soros, De Mesentier Silva, Togelius and Hoover, GECCO 2019 ([arXiv 1904.10656](https://arxiv.org/abs/1904.10656); details from the [full text](https://ar5iv.labs.arxiv.org/html/1904.10656)).
  - Descriptor: two deck-composition features computed before play, the mean and the variance of the 30 cards' mana costs.
  - Fitness: the sum of hero-health differences over 200 games per evaluation, with 10,000 evaluations per configuration. The pilot was the fixed SabberStone agent with aggro or control heuristics.
  - Sliding boundaries: cell boundaries sit at uniform percentiles of the observed distribution, not at uniform feature values. They are recomputed every δ=100 individuals by sorting along each feature. The grid also grows linearly from 2×2 to 20×20.
  - No baseline comparison and no QD-score are reported.
  - Single cards dominate whole classes: Sunwalker is in 99% of control paladin decks, and Earthen Ring Farseer in 96.5% of aggro hunter decks. The authors say "certain cards" may "push search toward local optima". [F1]
- **CMA-ME.** Fontaine, Togelius, Nikolaidis and Hoover, GECCO 2020 ([arXiv 1912.02400](https://arxiv.org/abs/1912.02400)).
  - It combines CMA-ES self-adaptation with a MAP-Elites archive. On a Hearthstone strategy search it found "a higher overall quality and broader diversity of strategies" than CMA-ES or MAP-Elites.
  - It "more than doubles the performance of MAP-Elites" on standard QD metrics.
  - It searches continuous parameters, here the weights of a policy, not discrete decks. A later deck-building paper used a 109-parameter neural heuristic trained with CMA-ME for 50,000 evaluations as its player ([DSA-ME](https://ar5iv.labs.arxiv.org/html/2112.03534)).
- **Background, not re-fetched this session.**
  - MAP-Elites: Mouret and Clune 2015, [arXiv 1504.04909](https://arxiv.org/abs/1504.04909). It keeps the best solution ("elite") per cell of a user-defined descriptor grid.
  - CVT-MAP-Elites: Vassiliades, Chatzilygeroudis and Mouret, IEEE TEVC 2018, [arXiv 1610.05729](https://arxiv.org/abs/1610.05729). It replaces the grid with k-means centroids, so the number of niches is fixed whatever the descriptor's dimension. That makes high-dimensional descriptors such as matchup vectors workable.
  - CMA-MAE: Fontaine and Nikolaidis, GECCO 2023, [arXiv 2205.10752](https://arxiv.org/abs/2205.10752).
  - Differentiable QD (CMA-MEGA): Fontaine and Nikolaidis, NeurIPS 2021, [arXiv 2106.03894](https://arxiv.org/abs/2106.03894).
  - CMA-MAE and CMA-MEGA need continuous parameters, or gradients of fitness and descriptors with respect to them, so they do not apply directly to card-count genomes.
- **Novelty search with local competition (NSLC).** Lehman and Stanley, GECCO 2011, pp. 211-218 ([PDF](https://groups.csail.mit.edu/EVO-DesignOpt/gecco2011Proceedings/proceedings/p211.pdf)).
  - Motivation: evolved virtual creatures "tend to converge to a single morphology because selection therein greedily rewards the morphology that is easiest to exploit".
  - Method: two objectives, novelty in morphology space and a local-competition score. That score counts how many of an individual's k nearest morphological neighbours it outperforms.
  - Results over 15 runs per variant: fitness-only and novelty-with-global-competition runs "generally converge to a single body plan". Local competition exploits more of the niches. "While global competition is better able to find the maximum fitness, local competition is better able to exploit all of the morphological niches." The exact values are only in figures. [F1]
- **Novelty search needs a bounded behaviour space.** Lehman and Stanley, *Evolutionary Computation* 19(2), 2011 ([PDF](https://www.cs.swarthmore.edu/~meeden/DevelopmentalRobotics/lehman_ecj11.pdf)).
  - In an unenclosed maze, novelty search solved 5 of 100 runs and fitness search 2 of 100. "Constraining the space of possible behaviors is important in some domains for novelty search to be efficient." [F1, F5]
- **AURORA, descriptors learned without hand coding.** Cully, GECCO 2019 ([arXiv 1905.11874](https://ar5iv.labs.arxiv.org/html/1905.11874)).
  - The descriptor is a PCA or autoencoder projection of raw sensory traces; in the experiments these are 100-dimensional trajectories projected to 2D.
  - The encoder is retrained on the growing archive on a schedule that slows over time (batches 0, 50, 150, 350, 750, 1550, 3150 of 5,000).
  - After each retrain every archived solution is re-encoded and reinserted, and collisions keep the better one. The archive shrinks after an update and then regrows. The distance parameter is recomputed to keep the maximum archive size constant.
  - Ballistic task (KLC, lower is better): hand-coded ≈0, AURORA-PCA 0.051-0.053, AURORA-AE incremental 0.097, CVT-MAP-Elites without a prior 3.2.
  - Air hockey: AURORA-AE was indistinguishable from the hand-coded descriptor (p=0.561).
- **AURORA, extended version.** Grillotti and Cully, [arXiv 2106.05648](https://ar5iv.labs.arxiv.org/html/2106.05648); the page names no venue.
  - Container-size control (CSC) adapts the novelty threshold, d_min ← d_min·(1 + K·(|C| − N_target)), to hold the archive near a target size.
  - Coverage was close to the hand-coded baseline in every task. Fitness was close in Maze and Hexapod but lower in Air-Hockey (p<2×10⁻⁶).
  - The learned descriptors captured features the hand-coded ones missed, such as body orientation.
  - Caveats: CSC "assumes no sudden global change to the BD space, such as an encoder reset". 2D latents can come out entangled.
- **PATA-EC, a domain-general characterisation from rankings.** Enhanced POET: Wang, Lehman, Rawal, Zhi, Li, Clune and Stanley, 2020 ([arXiv 2003.08536](https://ar5iv.labs.arxiv.org/html/2003.08536)).
  - An environment is described by the scores of every active and archived agent on it. Scores are clipped (failure and mastery carry no signal), replaced by ranks normalised to [−0.5, 0.5], and compared with Euclidean distance. Novelty is the mean distance to the k=5 nearest neighbours.
  - It replaced hand-coded terrain features that limited exploration to "prescripted possibilities".
  - Cost: it needed 82.4 ± 7.31% more computation to match the hand-designed characterisation.
- **Dominated Novelty Search.** Bahlous-Boldi, Faldor, Grillotti, Janmohamed, Coiffard, Spector and Cully, 2025 ([arXiv 2502.00593](https://arxiv.org/abs/2502.00593)).
  - It recasts QD as a genetic algorithm in which local competition happens through a fitness transformation instead of a grid or archive. It needs no predefined bounds and claims to keep its advantage in "high-dimensional and unsupervised spaces".
  - Only the abstract was read; no numbers verified.

### Inferences
- **The current loop already looks like crowding with global competition.** [F1, F3]
  - Each deck is replaced only by its own better-scoring edit, which is per-lineage crowding. Every deck is scored against the same population mix and the worst are replaced globally, which is global competition. NSLC finds this predisposes the population to converge on one body plan.
  - The ~10-card minimum distance from log #27 and the deck-type cap are crude niching. They do not change what each deck is optimised against.
- **Matchup-profile descriptor (PATA-EC applied to decks).** [F1, F2]
  - Pick a panel of K reference decks, for example the k-means centroids or elites of the current archive. Play each candidate deck against the panel with the shared pilot, then clip and rank-normalise its K win rates. Use that vector in a CVT archive.
  - It needs no human prior, transfers to MTG unchanged, and separates "walls" from prize-race decks by whom they beat, not by card counts.
  - Costs: K×n extra games per evaluation, and the descriptor moves when the panel or pilot changes. Re-encode the archive periodically, as AURORA does.
- **Rule-defined, game-agnostic descriptors.**
  - Candidates: average game length in turns (DSA-ME used it as a measure; see section 2), the share of wins by each rule-defined end condition (prizes, deck-out, opponent out of Pokemon), and cards in hand.
  - They are cheaper than matchup profiles and still carry to other games, because every card game's rules list its win conditions. A "win-condition mix" axis would keep prize-race decks as their own niche, so they are not out-competed by deck-out walls and Pokemon piles. [F1, F4, F5]
- **Do not use the evaluation metric as a descriptor axis in training.** A descriptor built on Pokemon / Trainer / Energy counts is human-chosen and is the very diagnostic used against the human lists. That risks leakage, and it may count as a prior under the "self-discovery, no priors" rule.
  - It is fine as an evaluation-only archive. Run MESB-style percentile cells over Energy count and Trainer count, with the current pilot as the evaluator. The best win rate per cell then shows whether low-Energy, high-Trainer decks can win under this pilot (a pilot problem, F2 and F4) or simply were never reached (a drafting problem, F1 and F3).
- **Sliding (percentile) boundaries.** If a hand-made descriptor is used, MESB-style percentile boundaries avoid choosing bounds. Combined with CVT they avoid empty cells in a 60-card space.

### Gaps
- No QD paper found on Pokemon TCG or MTG deck building; Hearthstone is the nearest analogue.
- MESB win rates exist only in figures, and the paper does not compare against plain MAP-Elites.
- NSLC's diversity and fitness numbers exist only in figures.
- Not read: Meyerson, Lehman and Miikkulainen 2016, "Learning behavior characterizations for novelty search". No source found on using a co-learned RL policy's own embedding as a QD descriptor; how AURORA behaves when the encoder is itself being trained by RL is untested in what I read.

## 2. QD-RL hybrids (PGA-ME, DCG-ME, QDax) and QD for game content and strategies (Hearthstone decks, game-playing strategies)

### Takeaway
The QD-RL literature names the same pathology as F3. A learned variation operator trained on global fitness drags offspring toward the single fitness optimum. The fix is to condition the critic and actor on a target descriptor. For decks, Deep Surrogate Assisted MAP-Elites (DSA-ME) shows that an online neural surrogate over card-count vectors multiplies what each real game buys. Adversarial QD (GAME) shows how to choose opponent panels so co-evolution does not collapse.

### Cited findings
- **PGA-MAP-Elites and why it collapses.** As described in Faldor, Chalumeau, Flageat and Cully, 2023 ([arXiv 2303.03832](https://ar5iv.labs.arxiv.org/html/2303.03832)).
  - Half of each batch comes from GA variation and half from a policy-gradient operator that uses a TD3 critic.
  - The critic estimates global fitness only, so in omnidirectional tasks "the global optimum for the fitness is the solution that does not move". The PG operator pushes offspring to collapse onto that one descriptor, and it is weak on deceptive tasks.
- **DCG-MAP-Elites (DCG-ME).** Same paper and source.
  - A descriptor-conditioned critic Q(s, a | d) scales reward by the similarity S(d, d′) = exp(−‖d − d′‖/l) between the achieved and the target descriptor.
  - Offspring are improved "while staying in their cell". A descriptor-conditioned actor π(s | d), trained alongside, distils the archive into one policy.
  - Setup: 20 seeds, 10⁶ evaluations, QDax/Brax tasks. QD-score rose 82% over PGA-ME on average. On Ant-Omni and the deceptive AntTrap-Omni it had the best QD-score (p<10⁻⁶) and coverage (p<10⁻⁴).
  - The distilled single policy stayed within ~3% of the archive's QD-score on the Ant tasks, but lost more than 40% on Hexapod-Omni and Walker-Uni.
- **QDax.** Chalumeau, Lim, Boige, Allard, Grillotti, Flageat, Macé, Flajolet, Pierrot and Cully, 2023 ([arXiv 2308.03665](https://arxiv.org/abs/2308.03665)).
  - A JAX library of QD, neuroevolution and RL algorithms that can be JIT-compiled for GPU or TPU. The abstract lists no speedups and does not name the algorithms included.
- **DSA-ME, Hearthstone deck building.** Zhang, Fontaine, Hoover and Nikolaidis, GECCO 2022, plus an ICLR 2022 workshop paper ([arXiv 2112.03534](https://ar5iv.labs.arxiv.org/html/2112.03534)).
  - Genome: a bag-of-cards vector of 0-2 copies over 180 candidate cards, 30 per deck.
  - Each evaluation is 200 games against 6 opponent decks, because "the outcome of a single Hearthstone game has high variance".
  - Objective: average health difference. Measures: average game length in turns (the aggro-to-control spectrum) and average cards in hand.
  - Loop: an MLP surrogate ([128, 32, 16]) is trained online on all real evaluations. An inner MAP-Elites runs on the surrogate for 10⁶ iterations, and the surrogate archive's elites are then evaluated in real games. Budget: 10,000 real evaluations.
  - Results (mean ± sd, 5 trials):

    | Method | QD-score | Cells filled | Max win % |
    |---|---|---|---|
    | MAP-Elites | 136.89 ± 1.95 | 14.36% | 90.6 |
    | Linear surrogate (LSA-ME) | 276.23 ± 6.10 | 27.89% | 96.2 |
    | DSA-ME | 338.52 ± 5.86 | 31.86% | 98.4 |

  - Only 44% of surrogate elites stayed in the archive after real evaluation, and only 3% stayed in the same cell (mean cell shift 2.45). The surrogate predicted the measures poorly.
  - Each trial took 10-12 h on 200 Xeon CPUs. [F1, F3]
- **GAME (Generational Adversarial MAP-Elites).** Anne, Syrkis, Elhosni, Turati, Legendre, Jaquier and Risi, 2025 ([arXiv 2505.06617](https://ar5iv.labs.arxiv.org/html/2505.06617)).
  - The two sides alternate by generation. Each side is illuminated by multi-task MAP-Elites against "tasks", which are opponents. The next tasks are the elites of 100 k-means clusters over the archive.
  - Descriptors: CLIP embeddings of 5 frames of each battle video (2,560-D, cosine distance, growing CVT archive), with no handcrafted features.
  - A quality-only variant and a variant without the embedding did significantly worse on coverage and QD-score. One quality-only replication fell to 0% novel behaviours after 8 generations, against ~60-90% for GAME variants.
  - Exact Elo numbers are only in figures. [F1, F2]
- **Tournament-informed task selection.** Anne et al., GECCO 2026 ([arXiv 2601.19562](https://arxiv.org/abs/2601.19562)).
  - Choosing opponent tasks by behaviour alone "may lead to undesired dynamics due to inter-side dependencies". Choosing them from an inter-variant tournament gave higher adversarial quality and diversity on Pong, cat-and-mouse and pursuers-evaders.

### Inferences
- **The REINFORCE draft head is a global-fitness variation operator.** [F3]
  - Its entropy collapse (3 → 0.5 nats), fresh heads re-converging onto the incumbent's cards, and exploiters drifting to the main type all match the PGA-ME pathology: a learned operator trained on global win rate pulls every offspring toward the global optimum.
  - Loop change (DCG-style draft head): condition the head on a target niche, π(edit | deck, d_target). Reward it with the edit's improvement within the niche (local competition), times a similarity kernel between the new deck's descriptor and d_target. One conditioned head could replace the 3-head league and acts as "archive distillation".
  - Keep a share of random (GA-style) card edits as well. DCG-ME still relied on GA exploration in the deceptive AntTrap task.
- **Surrogate-assisted deck search (DSA-ME-style).** [F3]
  - Use a cheap model to propose edits and spend real games only on confirming archive insertions. Candidate models: the pilot's start-of-game value v(A, B), or the matchup model planned in log #27.
  - DSA-ME's 3% same-cell rate says real games must set the descriptor; the surrogate can only screen candidates.
- **Pilot training distribution.** [F2]
  - Sample the pilot's self-play games uniformly over archive niches, not over population members. The F2 evidence that a varied population keeps the pilot general then holds by construction. The archive stays varied even when one niche's elite is strongest.
- **Opponent panels for deck fitness (GAME-style).** [F1, F2]
  - Score a deck against the elites of k-means clusters of the archive, not against the current population mix. When the mix is mostly walls, "beats the population" becomes "beats walls", and that self-reinforces F1.
  - Tournament-informed selection suggests picking panel members by their head-to-head results, not their descriptors alone.
- **Compute.** [inference]
  - At the ~16-19 games/s measured with the token pilot in log #27, DSA-ME's 2×10⁶ real games would take ~30-35 h. One generation of re-evaluating a 100-niche archive at 100 games per deck (10⁴ games) would take ~9-10 min.
  - JAX's CUDA builds are, to my knowledge, Linux/WSL2-only, so QDax would need WSL2 here. The algorithms are simple enough to reimplement in the existing PyTorch code.

### Gaps
- Not re-read: the original PGA-ME paper (Nilsson and Cully, GECCO 2021); its description comes from the DCG-ME paper.
- No source found on QD in which the evaluating pilot is itself trained on the archive. DSA-ME and MESB used fixed agents, and GAME evolves both sides with no learned pilot.
- QDax's exact algorithm list (AURORA, NSLC, etc.) is not confirmed from the abstract.
- No paper found applying DCG-style conditioning to a discrete edit policy.

## 3. Niching, fitness sharing, speciation (NEAT), innovation protection, deterministic crowding, and results on deceptive landscapes

### Takeaway
The NEAT ablation reads like F1's relapse. Without speciation, "the population quickly converges on whatever topology happens to initially perform best", draining diversity "within 10 generations". It was 7× slower and failed 25% of the time. Fitness sharing and per-species protection, not diversity injection, prevented this. Deterministic crowding, the closest classic to the current per-deck replacement rule, is reported to drift toward a single individual.

### Cited findings
- **NEAT speciation.** Stanley and Miikkulainen, *Evolutionary Computation* 10(2), 2002 ([PDF](https://nn.cs.utexas.edu/downloads/papers/stanley.ec02.pdf)).
  - "Speciating the population allows organisms to compete primarily within their own niches instead of with the population at large. This way, topological innovations are protected in a new niche where they have time to optimize."
  - It uses explicit fitness sharing (Goldberg and Richardson, 1987): "organisms in the same species must share the fitness of their niche. Thus, a species cannot afford to become too big even if many of its organisms perform well", so "any one species is unlikely to take over the entire population".
  - Other rules:
    - Compatibility threshold δ_t = 3.0 (4.0 in DPNV).
    - A species whose best fitness has not improved in 15 generations may not reproduce.
    - The champion of every species larger than 5 is copied unchanged.
    - If the whole population stalls for 20 generations, only the top two species reproduce.
- **NEAT ablation**, double-pole balancing without velocities. Averages over 20 runs, or 120 runs for full and nonmating NEAT.

  | Variant | Evaluations | Failure rate |
  |---|---|---|
  | Full NEAT | 3,600 | 0% |
  | Nonmating NEAT | 5,557 | 0% |
  | Initial-random NEAT | 23,033 | 5% |
  | Nonspeciated NEAT | 25,600 | 25% |
  | No-growth NEAT | 30,239 | 80% |

  - "Without speciation, the population quickly converges on whatever topology happens to initially perform best. Thus, a lot of diversity is drained immediately (within 10 generations)." The nonspeciated version had to start from a random population to have any diversity, and it was still 7× slower. [F1, F3]
- **Deception (maze navigation).** Lehman and Stanley, ECJ 2011 ([PDF](https://www.cs.swarthmore.edu/~meeden/DevelopmentalRobotics/lehman_ecj11.pdf)).
  - Medium maze: novelty search averaged 18,274 evaluations (sd 20,447) and fitness search 56,334 (sd 48,705), both solving all 40 runs (p<0.001). Random selection solved 21 of 40.
  - Hard maze: fitness search solved 3 of 40 and random selection 4 of 40. Novelty search solved 39 of 40 (35,109 evaluations on average) — "deception in this map renders the gradient of fitness no more helpful than random search".
  - Fitness-based solutions on the medium maze were nearly 3× larger (66.74 vs 24.6 connections, p<0.05). [F1, F5]
- **Deterministic crowding and fitness sharing, from search results only (full texts not read).**
  - In deterministic crowding (Mahfoud), an offspring can replace only its own parents ([review, arXiv 1508.05342](https://arxiv.org/pdf/1508.05342)).
  - McIntyre and Heywood (GECCO 2004) report "significant genetic drift" in deterministic crowding that hinders long-term niche maintenance, and prefer sharing for diversity and niche accuracy ([PDF](https://web.cs.dal.ca/~mheywood/X-files/Publications/andy-GECCO04.pdf)).
  - A 2005 study attributes deterministic crowding's convergence to a single individual to "replacement errors" ([Springer](https://link.springer.com/article/10.1007/s11771-005-0400-7)).

### Inferences
- **Speciate the deck population and share fitness within species.** [F1, F3]
  - Cluster decks by descriptor (section 1) into species. Give each species an edit and turnover budget in proportion to its fitness-shared total. Keep each species' champion unchanged. Let a species that stalls for N iterations die out; do not let it be overrun.
  - This differs from the current type cap. A cap limits the share of the leading type but leaves every deck optimising the same global objective, so the relapse within ~10-15 iterations resembles NEAT's nonspeciated drain "within 10 generations".
- **Innovation protection for new decks and heads.** [F3, F5]
  - A fresh draft head or a random/mutated turnover deck should compete only within its own species, or against an age-matched cohort, for a grace period. That stops it being judged at once against a long-optimised incumbent. NEAT's reason for speciation is that new structure needs "time to optimize".
  - This addresses fresh heads re-converging onto the incumbent's cards, and it may help F5, where from scratch everything collapses into Pokemon piles.
- **Per-deck replacement is deterministic crowding.** [F3]
  - "Deck moves to its edited version if it scores better" is crowding. Under noisy fitness, its replacement errors push toward one individual, which fits 73% of decks moving at the noise floor. Section 4 gives the noise fix.
- **Deception.** [F1, F5]
  - The maze results support the CLAUDE.md premise that a single win-rate objective can be deceptive. The walls are a local optimum the gradient leads into, and prize-race decks may be stepping stones that score worse at first under a weak long-horizon pilot (F4).

### Gaps
- Mahfoud's 1995 dissertation was not read.
- No niching result found specific to deceptive problems in discrete deck-like spaces.
- Age-layered population structure (Hornby's ALPS) is a related form of innovation protection, but it was not searched in this session.

## 4. Evaluation noise in QD (noisy fitness, re-evaluation, Flageat and Cully's "uncertain QD"), matching F3's noisy selection

### Takeaway
Elitist archives under noise fill with "lucky" solutions. Re-evaluating each new offspring a fixed N times is a poor fix at small budgets. The best general method in the Uncertain QD benchmark was Deep-Grid: keep D candidates per cell and let fitness-proportional selection within the cell plus continual reinsertion average the noise out. Archive-Sampling (re-evaluate the whole archive every generation, depth 2) won on the hardest task.

### Cited findings
- **Uncertain QD.** Flageat and Cully, 2023, submitted to IEEE TEVC ([arXiv 2302.00463](https://arxiv.org/abs/2302.00463); details from the [full text](https://ar5iv.labs.arxiv.org/html/2302.00463)).
  - Failure mechanisms:
    - Elitist QD algorithms "maintain lucky solutions", so final archives hold "a majority of lucky sub-performing solutions".
    - MAP-Elites keeps re-evaluating near-identical solutions "until they get lucky results".
    - Solutions with high descriptor variance populate more cells and survive more easily.
  - Methods compared:
    - MAP-Elites-sampling: evaluate every offspring N=32 times.
    - Adaptive-sampling (Justesen et al.): sequential and hard to parallelise.
    - Deep-Grid (Flageat and Cully, ALIFE 2020): D=32 solutions per cell, fitness-proportional roulette selection within the cell, every offspring added.
    - Archive-Sampling (new): re-evaluate the whole archive each generation, D=2.
    - Parallel-Adaptive-Sampling (new): evaluate each offspring as many times as the median archive member.
    - Deep-Grid-Sampling (new): N=8.
  - Results on Arm, Hexapod, Walker and Ant, with per-generation sampling budgets of 256-16,384:
    - Deep-Grid was "the optimal Uncertain QD approach in Arm, Hexapod and Walker whatever the sampling-size".
    - Archive-Sampling and Parallel-Adaptive-Sampling were best on Ant by corrected QD-score (p<5×10⁻⁴), but are undefined when the budget is below the archive size.
    - MAP-Elites-sampling was dominated by plain MAP-Elites at budget 256 (p<0.05), likely because it limits exploration.
  - Metrics: the corrected archive (median over M=512 re-evaluations per cell), QD-score loss, and a reproducibility score. [F3]
- **Hearthstone variance.** One game is so noisy that deck evaluation used 200 games per deck ([DSA-ME](https://ar5iv.labs.arxiv.org/html/2112.03534); [MESB](https://ar5iv.labs.arxiv.org/html/1904.10656)). [F3]

### Inferences
- **"73% of decks moved even when no candidate was better" is the lucky-elite effect.** [F3]
  - Moving to the best-scoring of several candidates is a max over noisy estimates, so it is biased upward (winner's curse). The incumbent's score is not refreshed.
  - Loop change: treat each deck niche as a depth-D cell (D=2-8) holding the incumbent and recent challengers, each with a running win count. Every generation, play fresh games for all cell members (Archive-Sampling), pool them with their past games, and pick the cell's elite by pooled mean or a lower confidence bound.
  - A lucky challenger then decays back to its true value. A significance gate, which this repo already found holds deck shape, becomes unnecessary for deck shape, and it also covers deck type because niches are per type.
- **Re-evaluation goes stale when the pilot changes.** [F2, F3]
  - After each pilot update, past games are stale. Down-weight them exponentially, or reset counts at pilot checkpoints, and re-evaluate the archive with the new pilot.
  - The DSA-ME-style surrogate (section 2) can be refit at the same time.
- **Report a "corrected archive".** Re-evaluate the final archive's elites with many games, and with an older generalist pilot as well, to separate real quality from noise and from pilot co-adaptation (F2's 0.72-0.76 vs 0.23-0.24 gap).

### Gaps
- Not read: Justesen, Risi and Mouret's "MAP-Elites for noisy domains by adaptive sampling" (GECCO 2019 companion), and Grillotti, Flageat, Lim and Cully's "Don't bet on luck alone" (GECCO 2023, on reproducibility). Their details come only from Flageat and Cully's summary.
- No uncertain-QD study found in which the noise source, a learning pilot, is non-stationary as well as stochastic.

## 5. Open-endedness arguments (Stanley and Lehman, POET) for why a single fitness drives to a local optimum, and what a deck-space QD archive judged by a co-learning pilot would need

### Takeaway
POET's results support the claim behind F1. Hard targets reached through stepping stones and transfer cannot be reached by optimising them directly (ES from scratch reached 13.6-39.6 against a success threshold of 230). The pieces carry over to a deck archive judged by a shared pilot: a minimal criterion for entry, novelty ranking among entrants, transfer between niches, and a domain-general characterisation (PATA-EC). The pilot plays the role of POET's "agents" and the deck niches the role of "environments".

### Cited findings
- **POET.** Wang, Lehman, Clune and Stanley, 2019 ([arXiv 1901.01753](https://ar5iv.labs.arxiv.org/html/1901.01753)).
  - Loop: keep environment-agent pairs, mutate environments, optimise agents with ES, and try transfers between environments.
  - Minimal criterion: a child environment is kept only if its paired agent scores between 50 and 300, neither too hard nor too easy. The most novel survivors are kept.
  - ES from scratch on POET-generated environments reached maxima of 17.9, 39.6, 13.6, 24.0 and 19.2, against POET's success threshold of 230 (p<0.01).
  - Without transfer, POET solved no extremely challenging environment and covered significantly less of the environment space (p<2.2×10⁻¹⁶).
  - A direct-path curriculum matched POET only on the easiest environments.
  - Direct optimisation produced "premature convergence to degenerate behavior": agents froze before obstacles to avoid the −100 fall penalty. A flat-ground agent improved only after a skill transferred back from a stump environment.
  - Argument: the path to a good solution runs through stepping stones that do not resemble the goal, so they cannot be known in advance. [F1, F5]
- **Enhanced POET.** Wang et al., 2020 ([arXiv 2003.08536](https://ar5iv.labs.arxiv.org/html/2003.08536)).
  - PATA-EC (section 1).
  - A stricter transfer rule: both the direct and the fine-tuned score must beat the maximum of the incumbent's last 5 scores. This gave the same diversity with 79.7 ± 1.67% of the computation and cut agent replacements from 50.44% to 22.31%.
  - ANNECS (accumulated number of novel environments created and solved) as a measure of open-endedness. Original POET plateaued after ~20,000 iterations, while Enhanced POET kept rising almost linearly. [F2, F3]
- **The book version of the argument.** Stanley and Lehman, *Why Greatness Cannot Be Planned: The Myth of the Objective*, Springer 2015 ([Springer](https://link.springer.com/book/10.1007/978-3-319-15524-1); not re-read this session). It is the book-length form of the deception and stepping-stone argument that the POET and novelty-search papers above make with data.
- **Adversarial open-endedness.** GAME (section 2) frames co-evolution as an arms race that must avoid one side collapsing or both settling "into a stable equilibrium where both sides stop innovating" (citing Ficici and Pollack). It credits the AlphaStar league with avoiding "strategy collapse" and forgetting ([arXiv 2505.06617](https://ar5iv.labs.arxiv.org/html/2505.06617)). [F1, F2]

### Inferences: what a deck-space QD archive judged by a co-learning pilot would need
1. **Niches defined without human priors.** Use a matchup-profile (PATA-EC) or rule-outcome descriptor (section 1), held in a CVT or unstructured archive with container-size control. Re-encode the archive whenever the panel, encoder or pilot changes. [F1]
2. **Local competition and fitness sharing.** A deck is replaced only by a better deck in its own niche. The edit and turnover budget is shared across species, and champions are preserved (sections 1 and 3). [F1, F3]
3. **Noise-aware elites.** Depth-D cells, re-evaluation of the archive with pooled game counts, and an elite chosen by lower confidence bound (section 4). [F3]
4. **A minimal criterion for new niches.** A new deck enters only if its win rate against the panel lies in a band, for example 0.2-0.8 (my choice of numbers). Random piles and degenerate decks then do not take niches, while weak-but-viable stepping stones survive. [F5, F6]
5. **Transfer between niches.** Periodically try the elite edits, or the card packages, of one niche in neighbouring niches, and accept only under Enhanced POET's stricter rule (beat the best recent score). That reduces noisy acceptances. [F3]
6. **Pilot generality as a design constraint.** Sample self-play games uniformly over niches. Judge deck fitness with the current pilot and, as a check, a frozen generalist pilot, or a small panel of pilot snapshots. That separates real deck strength from deck-pilot co-adaptation, giving a PATA-EC view in the pilot dimension. [F2]
7. **Pick the meta from the archive, do not take its argmax.** QD keeps the niches. The "metagame" is then a game-theoretic solution over the archive elites' empirical payoff matrix (PSRO / Nash, covered by other notes).
   - Human-likeness then depends on whether non-wall niches become competitive as the pilot improves (F4). QD makes that test possible, because those niches still exist when the pilot catches up. It does not by itself fix the long-horizon tactical weakness. [F2, F4]
8. **An open-endedness metric.** Track an ANNECS-like count of new niches that pass the minimal criterion and later beat a fixed panel. A flat curve is the signal to stop a run early, per CLAUDE.md. [all]

### Gaps
- No open-endedness paper found in which a single shared learner (one pilot) is judged on all niches. POET pairs one agent with each environment, which would reintroduce F2's specialisation if copied literally. Whether one shared pilot can support many niches is untested in what I read.
- The 0.2-0.8 minimal-criterion band and the 5-score transfer window are my parameters, carried over from POET's 50-300 band and Enhanced POET's rule. They are not tested values for decks.

## 6. Mapping: which failure mode each finding bears on, and what to change in the loop

### Takeaway
The highest-value, compute-frugal changes, in order:
1. Speciation or niching with local competition and fitness sharing, replacing the type cap and global turnover (F1, F3).
2. Depth-D noise-aware elites with archive re-evaluation, replacing best-of-candidates moves (F3).
3. A descriptor-conditioned draft head trained on within-niche improvement, replacing the globally rewarded REINFORCE head and exploiters (F3).
4. A domain-general matchup-profile descriptor, plus opponent panels drawn from archive clusters (F1, F2).
5. Pilot self-play sampled uniformly over niches (F2).

QD does not directly fix F4, the long-horizon tactics. It keeps prize-race niches alive while that is worked on elsewhere.

### Cited findings
- Global competition converges to a single body plan, while local competition keeps niches at some cost in peak fitness ([NSLC, GECCO 2011](https://groups.csail.mit.edu/EVO-DesignOpt/gecco2011Proceedings/proceedings/p211.pdf)). → F1
- Without speciation, diversity drains within 10 generations: 25% failure, 7× slower ([NEAT, ECJ 2002](https://nn.cs.utexas.edu/downloads/papers/stanley.ec02.pdf)). → F1 (relapse in ~10-15 iterations), F3
- A policy-gradient operator on global fitness collapses offspring to one descriptor, and descriptor conditioning gives +82% QD-score ([DCG-ME](https://ar5iv.labs.arxiv.org/html/2303.03832)). → F3 (draft-head collapse, exploiters drifting)
- Elitism under noise keeps lucky solutions, and Deep-Grid and Archive-Sampling are the best fixes ([Uncertain QD](https://ar5iv.labs.arxiv.org/html/2302.00463)). → F3 (73% moved at the noise floor)
- An online deep surrogate gave 2.5× the QD-score of MAP-Elites for the same 10,000 real evaluations, but surrogate-predicted cells were rarely right ([DSA-ME](https://ar5iv.labs.arxiv.org/html/2112.03534)). → compute constraint, F3
- A domain-general characterisation from agent rankings needed ~82% more compute than hand-designed features ([Enhanced POET](https://ar5iv.labs.arxiv.org/html/2003.08536)). → F1, without priors
- Opponent tasks as archive cluster elites, with no handcrafted descriptors; a quality-only variant lost novelty ([GAME](https://ar5iv.labs.arxiv.org/html/2505.06617); [tournament-informed](https://arxiv.org/abs/2601.19562)). → F1, F2
- Deceptive objectives: fitness search solved 3 of 40 hard mazes, novelty search 39 of 40, but novelty search needs a bounded behaviour space ([Lehman and Stanley, ECJ 2011](https://www.cs.swarthmore.edu/~meeden/DevelopmentalRobotics/lehman_ecj11.pdf)). → F1, F5
- Stepping stones and transfer reach environments that direct optimisation cannot ([POET](https://ar5iv.labs.arxiv.org/html/1901.01753)). → F1, F5

### Inferences
- **A minimal first experiment (my design).**
  - Keep the pilot, the edit proposals and the game engine. Change only the deck population:
    - ~100 CVT niches over a matchup-profile descriptor, against a panel of 8-16 cluster elites, re-clustered every few iterations.
    - Depth D=4 per niche, with pooled games and lower-confidence-bound elites.
    - Local replacement inside niches, and the turnover budget shared by niche.
  - Pilot self-play sampled uniformly over niches.
  - Evaluation only: a corrected archive against the 24 human lists, with both the current and the generalist pilot, plus the per-niche median Energy and Trainer counts.
  - Stop rule: if the archive's best non-wall niches do not close the gap to the walls in N iterations, and the global Nash support is still walls, then the bottleneck is the pilot (F4), not drafting. That outcome is itself diagnostic.
- **F4 and F6 are mostly outside QD's reach.** At most, a "game-length" or "win-condition" descriptor keeps short-game prize-race decks from being out-competed while the pilot's long-horizon play is fixed by other means. A turn limit (F6) is not needed for that.
- **F5 (from scratch).** Speciation with innovation protection, a bounded behaviour space, and a minimal criterion that excludes 0%-win random piles are the parts most likely to stop the deck-out pile collapse. This is untested.
- **Ground-truth caution.** If the descriptor uses card-type counts, keep it evaluation-only. The archive must not be steered toward the human Energy count; otherwise the "no priors / human lists for evaluation only" rule is broken.

### Gaps
- None of the cited works combine all of: a discrete deck genome, a learning RL pilot shared across niches, and a two-player metagame. The combination proposed here is inference.
- No exact cost figures for matchup-profile descriptors in card games. The ~9-10 min per 10⁴ games estimate uses log #27's games/s, which may have changed with the current pilot.
