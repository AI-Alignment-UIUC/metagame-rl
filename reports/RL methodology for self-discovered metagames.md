# Diversity Methods Keep Only What the Judge's Payoff Matrix Holds

The second literature sweep covered 79 ideas from 11 research angles. Of 357 fact-checked claims, 254 were verified, 92 partly verified, 9 found wrong and 2 left unverified. Its answer to "how do we prevent mode collapse and explore the full space?" is an order of work more than a method.

Every way of keeping a population diverse reads a payoff matrix. A resolved Condorcet winner takes all of the mass under max-entropy Nash and maximal lotteries, and under alpha-Rank in the limit ([Balduzzi et al. 2018](https://arxiv.org/abs/1806.02643); [Lanctot et al. 2023](https://arxiv.org/abs/2312.03121)). Under the population pilot, one wall already beats all 24 human lists, with a minimum of 0.531 at 32 games a pair (plan C27). Inside the human field, the learned judges find a cyclic share of 0.21-0.25 and an equilibrium led by Wigglytuff and Haymaker (JF2, log #149). The judge's game decides first; the selection rule decides second.

Where a matrix does hold cycles, the measured remedies are large:

- Local competition took coevolution from 0% to 67-78% success ([Mitchell 2006](https://melaniemitchell.me/PapersContent/CoevolutionaryLearning2006.pdf)).
- Of three evaluation regimes, only resetting the controller to broad weights each generation kept the designs diverse ([Strgar & Kriegman 2026](https://arxiv.org/abs/2502.10862)).
- Training a proposer for its best-of-K raised a solve rate from 12 to 84, where entropy regularisation reached 25 ([Walder & Karkhanis 2025](https://arxiv.org/abs/2505.15201)).
- Luck correction cut the standard deviation of results by 68%, giving the same significance from a tenth of the games ([Burch et al. 2018](https://arxiv.org/abs/1612.06915)).

All of these come from deterministic benchmarks, or from games far from a 60-card card game judged on about 10 noisy games. No angle found a card-game paper that rebuilt a human metagame's deck composition from self-play.

The literature therefore supplies an order of work and stop rules. First audit the judge's game (plan C07, C13, C16). Then separate drift from signal in the draft head (C24) and rule out a mis-specified game (C02, C13, C14). Only then spend screens on selection and diversity (C27, C42, C43). The research loop collapsed like the population: 19 of 27 screens reuse a recipe, and 25 of 27 fork from two wall states. The methodology literature prescribes the same cure for both: rival hypotheses, crucial experiments, measured noise floors and written triggers for looking outside the system.

## Collapse has six generators, and metagame-rl shows all six

The 11 angles split mode collapse into six mechanisms. Each has its own literature, its own signature in the project's data and, the new part, a diagnostic that can rule it in or out without a training screen. The first review ([RL literature on metagame collapse](RL%20literature%20on%20metagame%20collapse.md)) covered the judge and selection noise. This one adds the solution concept, the evaluation regime, the proposer's dynamics, the game's specification and the research process.

| Generator | What produces it in the literature | Project signature | Nodes / families | Plan |
|---|---|---|---|---|
| A Condorcet winner or single sink in the judge's game | Every solution concept concentrates on it (Balduzzi; Lanctot 2023; Omidshafiei) | Under the population pilot wall #829 beats all 24 lists; under pilot-v2, 15 of 24 lists beat all three walls (C27) | N4, N5, N7; H18, H22, H23 | C07, C13, C16, C21, C27 |
| The evaluation regime | A co-trained evaluator collapses designs to one species, a frozen one to clones of its favourites (Strgar & Kriegman) | The verdict follows the walls' pilot: own/own 0.72, v2/v2 0.24 (#137) | N4, N8; H18-H21, H43, H44 | C17, C20, C38, C39 |
| Global selection against the field | Truncation cannot hold a mixed equilibrium; focusing on one dimension (Ficici; Bucci & Pollack) | The gate holds the shape, yet decks with both Chansey and Snorlax rise from 53 to 73-80 of 99 (#140) | N5, N7; H24-H26, H36-H42 | C27, C32, C43, C44 |
| A learned proposer | Expected-reward maximisation converges to a point; frequencies drift with no signal (Jain; Doerr & Zheng) | Incoming entropy 2.745 → 0.50 nats in 20 iterations (scr-ctl479); accepted moves track proposals | N6; H27-H35 | C23, C24, C25, C41, C42 |
| Evaluation noise | The best of noisy candidates keeps lucky edits; unpaired comparisons count luck twice (AIVAT; Pollack & Blair) | 3 candidates at about 10 games move 73% of decks under a null | N5, N12; H24, H25, H62 | C03, C26, C29 |
| Valleys and a mis-specified game | Lexicase is no better than random at crossing valleys (DOSSIER); termination rules set the optimum (Krakovna; Pardo) | Walls score 0.36 in games of 40 turns or fewer and 0.78 beyond (#141); walls to Haymaker is about 8-10 coordinated changes | N1, N2, N9, N10; H01-H04, H45, H51 | C02, C13, C14, C28, C30, C36 |

The generators feed each other: the judge writes the matrix that selection reads, and the proposer supplies what selection accepts. That is why fixing one at a time held the shape but not the type.

## Every solution concept hands a Condorcet winner the whole population

An antisymmetric payoff matrix splits into a rating part and a cyclic part. The max-entropy Nash is uniform when the game is purely cyclic, and sits on the top-rated strategies when it is transitive ([Balduzzi et al. 2018](https://arxiv.org/abs/1806.02643)). Maximal lotteries are Condorcet-consistent and identify cycles ([Lanctot et al. 2023](https://arxiv.org/abs/2312.03121)). alpha-Rank keeps mass only on sink components: six of ten agents in a soccer meta-game, and one of seven AlphaGo variants ([Omidshafiei et al. 2019](https://arxiv.org/abs/1903.01373)).

Hence a stop rule. If the walls are a resolved Condorcet winner under a judge, no scoring rule, population structure or diversity bonus can keep another type under that judge. The fact-check narrowed this: the property holds strictly for Nash and maximal lotteries, and for alpha-Rank only as alpha grows without bound. At alpha 50, the SimpleBot matrix keeps an effective number of 5.19.

The project's evaluation-only matrices already say a good deal:

- **The walls under the population pilot.** Wall #829 beats every list: minimum 0.531, 20 of 24 edges resolved at 2 SE, none lost (plan C27).
- **The human field.** Within it the judges are not globally non-human. The Hodge audit gives transitive shares of 0.75 / 0.60 / 0.65 under SimpleBot, the scr-resetcap 499 pilot and pilot-v2. The cyclic shares, net of binomial noise, are 0.21 / 0.25 / 0.21. The logit equilibrium lies within total variation 0.10-0.25 of the real field under the population pilot, and 0.10-0.40 under pilot-v2 (log #149).
- **The cycles are weaker than they look.** The learned pilots' Nash supports are exact 0.500 ties around weakly unbeaten lists, not resolved cycles. SimpleBot's cycle edge (0.54) would need about 620 games to resolve.
- **Resolution is the bottleneck.** At 32 games a pair, only 99-108 of 276 edges resolve. ResponseGraphUCB stops sampling a pair once its intervals separate, and exploiting symmetry cut one instance from 244 interactions to 20 ([Rowland et al. 2019](https://arxiv.org/abs/1909.09849)). An indifference zone is still needed, because at 64 games edges within ±0.125 of 0.5 never resolve.

Two corrections change how such an audit should be read.

1. **No mixed attractor exists to aim for.** The judge's payoffs are constant-sum (1 / 0.5 / 0), so every population state earns one half. No mixed evolutionarily stable state exists, and an interior Nash is neutral under the continuous replicator and unstable under the discrete one ([Ficici 2004](http://demo.cs.brandeis.edu/papers/ficici_thesis_04.pdf)). The audit should report Nash support, cyclic share and the number of independent axes, not a mixed replicator attractor.
2. **Scoring alone cannot keep a cycle.** In a finite, well-mixed population, two of three rock-paper-scissors species die out after a mean time of about 0.62N ([Reichenbach, Mobilia & Frey 2006](https://arxiv.org/abs/q-bio/0605042)). Population places must follow the equilibrium, or the population needs spatial structure.

The ground truth needs the same care. Real metagames are not equilibria of their own matchup matrices. In modern Pokémon TCG data, the most-played deck held 15.5% of the field with a 46.7% expected win rate and 0% Nash weight ([Ramos & Soria 2026](https://arxiv.org/abs/2607.08692)). The target is deck composition and strength under strong play, not archetype shares.

Nodes N4, N5, N7; families H18, H22, H23, H39, H41. Three plan candidates are parked for cycle 2: C16 (the full audit, with a human-free decision of record), C27 (selection rules simulated on measured matrices) and C21 (judge variance). Under the cheaper spend, the Tier A probes C07 and C13 supply the judge rows they need.

## The evaluation regime decides whether a design population collapses

Strgar and Kriegman ran three evaluation regimes on one co-design problem ([Strgar & Kriegman 2026](https://arxiv.org/abs/2502.10862)):

- A controller trained alongside the population collapsed it to "a single species of similar designs which simplifies shared control".
- A frozen pretrained controller collapsed it to "slightly modified clones of the designs that are the most compatible with the pretrained model".
- Resetting weights and optimizer to the pretrained checkpoint every generation, then fine-tuning 60 steps on the current population, "significantly increases and sustains diversity as well as performance".

metagame-rl has run the first two regimes and from-scratch co-design, and each collapsed as described. The co-trained main line went to walls. A frozen pilot-v2 drafting from wide decks went to Pokémon piles (median Pokémon 15 to 23 in four iterations, #131). The from-scratch recipe went to piles with 85-99% deck-outs (#124, #132).

The reset regime is untried, but the evidence for it is thin. "Significantly" has no statistical test behind it, and the result rests on 3 trials in one differentiable-simulation domain, pretrained on over 10 million designs. The project also lacks a broad checkpoint to reset to. scr-anchor 472 already rates the walls 0.694 (#147). Pilot-v2 learned on random decks drawn from the human field's 56 cards, with deck-out wins paid 0. The plan therefore gates C39 (reset-and-fine-tune judge) on C17, and on a human-free starting checkpoint such as C30's warm-up pilot.

Two strands of the literature explain why a co-trained judge favours simple decks.

**Short evaluations favour fast learners.** Across 250 soft-robot designs, learning speed and ceiling were uncorrelated (Spearman 0.05), and budgets of up to a third of convergence selected steeper early curves ([Song et al. 2026](https://arxiv.org/abs/2608.23100); unreviewed, with significance shown for one task). Greedy population-based training lost ImageNet accuracy: 71.7%, against 76.5% for FIRE PBT, which compares learning curves only over their shared range ([Dalibard & Jaderberg 2021](https://arxiv.org/abs/2109.13800)). Splitting a shared evaluator helps only modestly: Kendall tau rose from 0.54 to 0.65 with 5 sub-supernets ([Zhao et al. 2021](https://arxiv.org/abs/2006.06863)).

**A part judged with mediocre partners settles on what needs no skill.** Cooperative coevolution is "more attracted to points of robust resting balance than to ideal collaboration". Biasing evaluation toward the ideal collaborator raised convergence to the optimum from under 10% to over 90% of 250 runs, though small changes in the bias rate swung that by 70-80% ([Panait, Wiegand & Luke 2004](https://cs.york.ac.uk/rts/docs/GECCO_2004/Conference%20proceedings/papers/3102/31020573.pdf)). The project fits this. The walls gain nothing from their own one-turn search (0.578 → 0.573), while the human lists gain 0.13-0.16 (#139, #146). Monte Carlo search shows the same from the judge's side: "Making playouts play better often causes the Monte-Carlo program to get weaker". Balancing a playout policy's errors, instead of raising its strength, took one program from 68.9% to 77.9% against Fuego ([Huang, Coulom & Lin 2010](https://www.remi-coulom.fr/CG2010-Simulation-Balancing/SimulationBalancing.pdf)). In the 2020 Hearthstone AI Competition, one aggro deck scored 0.33-0.41 under greedy agents and 0.60-0.66 under lookahead agents, though the agents also differed by author ([Hearthstone AI Competition 2020](https://hearthstoneai.github.io/botdownloads.html)).

The scoring rule decides whether a stronger judge can matter at all. Re-running `rl/metagame.py judged()` shows that `--judge-score min` never raises a deck above its greedy score. A wall at greedy 0.72 and searched 0.57 keeps 0.72 with 2 or 10 searched games, and reaches 0.70 only at 30. scr-jsearch479 flipped 6 selection decisions, where redraw noise alone predicts about 15 (analysis §9).

The fix is to estimate the searched verdict itself and to use paired greedy games only as a control variate. That estimate is unbiased for any coefficient and cuts variance by 1 − ρ² ([Veness, Lanctot & Bowling 2011](https://proceedings.neurips.cc/paper_files/paper/2011/file/d736bb10d83a904aefc1d6ce93dc54b8-Paper.pdf)). Searched games set the cost: at 100 searched games an iteration, about 60% of candidates get none. Hence the plan's order: the offline acceptance audit (C20) and the GPU-served search path (C03, Tier B) come before any in-loop powered judge (C38).

A pilot that had lost plasticity would also under-read new deck types. PPO does lose plasticity under distribution shift ([Juliani & Ash 2024](https://arxiv.org/abs/2405.19153), significant only under the permute shift; [Dohare et al. 2024](https://www.nature.com/articles/s41586-024-07711-7): PPO "fails catastrophically" when friction changes). But the KL anchor moved this pilot 65-70 Elo in 12 iterations (#138), and a varied field restored its generality (#137). Both point to data bias rather than lost plasticity. A plasticity probe with the policy held fixed (C22, parked) should decide before any reset or distillation earns a slot.

Nodes N3, N4, N8, N11; families H15-H23, H43, H44, H56. C07 is in Tier A and C17 is conditional; C20, C21, C22, C38 and C39 are parked.

## Global selection drains niches, and local or per-opponent selection keeps only real cycles

Scoring a deck by its mean result against the current population is Ficici's "best in the ecology", a frequency-dependent and non-monotonic solution concept ([Popovici et al. 2012](https://www.cs.tufts.edu/comp/150GA/handouts/nchb-main.pdf)). Add "replace the parent only if strictly better", as `--select` does, and it becomes Bucci and Pollack's population hill-climber. On their focusing game that hill-climber "focused entirely on the horizontal dimension", though the result rests on single qualitative runs ([Bucci & Pollack 2003](http://www.demo.cs.brandeis.edu/papers/bucci_gecco_focus_03.pdf)). Truncation, ranking and tournament selection "unconditionally fail to achieve polymorphic Nash equilibrium" in variable-sum games with mixed attractors ([Ficici, Melnik & Pollack 2005](https://doi.org/10.1109/TEVC.2005.856203)).

The project shows the signature. The gate cut moves from 65-83 to 13-28 an iteration, and held the largest type at 12-26 against the control's 33-74. Yet each accepted move still added 0.7-2.5 Pokémon and cut 0.2-1.9 Trainers, and decks with both Chansey and Snorlax rose from 53 to 73-80 (#140). The soft type cap was overrun whenever it bound: 72-76 decks against a limit of 49.5.

**Local competition has the strongest evidence.**

- In spatial coevolution, with each host judged on its 9 neighbours, runs succeeded 78% (39/50) and 67% (20/30) of the time. Non-spatial coevolution scored 0/50 and 0/20, and resource sharing 12% and 0% ([Mitchell 2006](https://melaniemitchell.me/PapersContent/CoevolutionaryLearning2006.pdf)).
- Three E. coli strains in a rock-paper-scissors relationship coexisted for at least 66 generations on static plates, and lost two strains when mixed ([Kerr et al. 2002](https://www.bcp.fu-berlin.de/biologie/arbeitsgruppen/zoologie/ag_steppuhn/lehrveranstaltungen/1_Theoretische-Oekologie_Kerr-et-al-2002.pdf)).
- Above a critical mobility, biodiversity is lost ([Reichenbach, Mobilia & Frey 2007](https://arxiv.org/abs/0709.0217)).

All of this needs cyclic dominance. If the walls dominate transitively, a torus only slows the sweep, though the speed of the wall front then measures transitivity under each judge. Spatial embedding can also sharpen over-specialisation ([Cartlidge 2005](https://etheses.whiterose.ac.uk/1315/1/cartlidge.pdf)).

**Per-opponent credit keeps the specialists that the mean discards.** Lexicase selection returns only Pareto-boundary individuals ([La Cava et al. 2019](https://arxiv.org/abs/1709.05394)). It solved the 3-bit multiplier in 100 of 100 runs, where tournament selection solved none ([Helmuth, Spector & Matheson 2015](https://www.cs.hamilton.edu/~thelmuth/Pubs/lexicase-IEEETEC-2014.pdf)).

- **Noise is the catch.** On continuous errors, plain lexicase ranked 6.83 of 8 methods, near random selection's 7.83, while ε-lexicase ranked 1.67 ([La Cava, Spector & Danai 2016](https://cavalab.org/assets/papers/La%20Cava%20et%20al.%20-%202016%20-%20Epsilon-Lexicase%20Selection%20for%20Regression.pdf)).
- **It does not cross valleys.** Lexicase did no better than random at valley crossing, and fitness sharing did best ([DOSSIER](https://arxiv.org/abs/2204.13839)).
- **No game precedent.** No angle found lexicase used in competitive coevolution or game agents.
- **Competitive fitness sharing alone is weak.** On Othello, tests rewarded for the distinctions they make were the lowest method (79.97%), and the gain came from adding random opponents (86.44%) ([Jaśkowski et al. 2013](https://www.cs.put.poznan.pl/mszubert/pub/jaskowski2013gecco.pdf)).

**A deduplicated opponent panel removes the field's bias toward the mirror.** One redundant copy of an agent moves two other agents' Elo by −63 and +63, while max-entropy Nash averaging is invariant to it ([Balduzzi et al. 2018](https://arxiv.org/abs/1806.02643)). With 73-80 of 99 decks being walls, the current field mostly tests the mirror. Opponent sets chosen by clustering tournament-rank vectors gave a cat-side win rate of 56.7%, against 42.0% for behaviour-chosen and 39.5% for random sets, with ties in Pong ([Anne et al. 2026](https://arxiv.org/abs/2601.19562)). Filtering out "opportunistic" variations, which gain against current opponents but lose against a well-differentiated set, produced progress where vanilla coevolution showed none ([Simione & Nolfi 2019](https://arxiv.org/abs/1909.08303)). It also beat hall-of-fame and archive methods: predator champions scored 0.572 against 0.282-0.415 ([Nolfi & Pagliuca 2024](https://doi.org/10.3389/frobt.2024.1470886)).

Archives and niching have costs. A best-of-generation memory stayed exploitable, at 0.375-0.758 against about 0 for a Nash memory ([Ficici & Pollack 2003](http://demo.cs.brandeis.edu/papers/ficici_gecco03.pdf)). On the realistic Tartarus problem, archives did no better than plain coevolution ([de Jong & Bucci 2006](http://demo.cs.brandeis.edu/papers/dejong_bucci_gecco2006.pdf)). Dominated Novelty Search lowered win rate in adversarial Pong, 55.4/59.3% against 59.7/63.5% (Anne et al. 2026). The human field has a dominant archetype (Wigglytuff, 10 of 24 lists), so niche results should be read by each niche's best deck against the lists, not by population shares.

Nodes N5, N7; families H24-H26, H36-H42. Four plan candidates cover these rules, all parked: C27 (rules simulated on measured matrices), C32 (a DOSSIER-style surrogate testbed), C43 (Evan's league of three heads with local judging) and C44 (a hard cap on a deck descriptor that can see the walls). The opportunistic-variation filter has no plan id.

## A learned proposer collapses through its objective, its update dynamics and its base measure

**Objective.** Maximising expected reward converges to one candidate. MOReinforce converged to a single candidate per preference, with QM9 diversity of 0.53 against a GFlowNet's 0.93 ([Jain et al. 2023](https://arxiv.org/abs/2210.12765)). PPO's top 1,000 molecules had a mean Tanimoto similarity of 0.62, against 0.44 for a GFlowNet ([Bengio et al. 2021](https://arxiv.org/abs/2106.04399)).

`--select` keeps only the best of K draws, so the head should be trained for the maximum. Three results support this:

- Pass@k training raised Gemma2-9B's cumulative ARC-AGI-1 solve rate from 12.00 to 84.14, against 24.67 with entropy regularisation ([Walder & Karkhanis 2025](https://arxiv.org/abs/2505.15201)).
- Winner-takes-all credit cut a TSP100 optimality gap from 0.27% to 0.07% at 16 samples ([Grinsztajn et al. 2023](https://arxiv.org/abs/2210.03475)).
- Gumbel-top-k sampling gives distinct candidates ([Kool, van Hoof & Welling 2019](https://arxiv.org/abs/1903.06059)).

Every one of these sources has deterministic rewards, and winner-only credit on 10-game means rewards lucky draws. So C42 (best-of-K credit) waits on C24.

**Dynamics.**

- **Drift without signal.** With no fitness signal at all, an estimation-of-distribution algorithm drives a frequency to its boundary, in Θ(μ/ρ²) iterations for PBIL ([Doerr & Zheng 2020](https://arxiv.org/abs/1910.14389)). The significance-based cGA avoids this by updating only on a significant deviation ([Doerr & Krejca 2020](https://arxiv.org/abs/1807.03495)).
- **Step size locks in.** On a two-armed bandit, 5%, 14% and 22% of runs locked onto the worse arm at step sizes 0.05, 0.10 and 0.15 ([Chung et al. 2021](https://arxiv.org/abs/2008.13773)).
- **Entropy terms are a weak lever.** Under softmax policy gradient, entropy changes by about −η·Cov(log π, π·A). An entropy loss of 0.01 "exploded", while covariance-targeted updates lifted a 32B model from 45.8 to 52.2 ([Cui et al. 2025](https://arxiv.org/abs/2505.22617)).

In scr-ctl479 the head's incoming entropy fell from 2.745 to 0.50 nats in 20 iterations. The generators angle estimates a per-card advantage standard error near 0.06 an iteration, against single-card effects of about 0.006-0.03 (#92). The head's rotation through one favourite card at a time may therefore be drift. C24's head bench with null and planted rewards (Tier A) settles this in about an hour of GPU after three hours of code. C25's frozen and null-reward forks run only if the bench leaves it open.

**Base measure.** Every exploration device flattens the proposal toward uniform over 277 card identities, and a uniform draw is 81% Pokémon and 2% basic Energy (#124). Every near-uniform head raised the Pokémon count. Fresh exploiters that lost 95-98% of their games, a near-null signal, still drafted 29/17/13 and 37/11/12 (#125).

Origin-fixation theory transfers proposal bias into the population only at low mutation supply, and this loop is high-supply, so the fact-check rated the analogy only partly applicable ([Yampolsky & Stoltzfus 2001, via Wikipedia](https://en.wikipedia.org/wiki/Bias_in_the_introduction_of_variation)). The logs show what happens instead. Regressing accepted changes on proposed ones gives slopes of 0.98 / 0.99 / 1.17 (Pokémon / Trainers / Energy) in scr-ctl479, and 0.81 / 0.78 / 0.50 under the gate. That is near-neutral selection at about 10 games a candidate. At the 479 fork the floored head proposed −0.1 Pokémon a draw, and after 486 accepted moves carried 0.18 more Energy than proposed. The walls' Energy excess is selected by the judge, not proposed.

A base-measure fix therefore mainly targets from-scratch Pokémon piles (F5): C41 (parked), and C40, Evan's ruling on the kind-aware constants (Tier A item 4). The entropy bonus also pulls toward uniform over identities, and must be re-targeted along with the base measure.

**What does not fit the budget.**

- **Diversity-filter memory.** It raised unique scaffolds from 2,635 to 20,712 in drug design ([Blaschke et al. 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7654024/)). But a binary filter was gamed ([Thomas et al. 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9531503)), and diversity pressure drifts into the high-volume region of object space ([Renz et al. 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11323242/)), which here is Pokémon. A reward that is not game results also conflicts with rule 3.
- **GFlowNets.** They cover modes at 10^5-10^6 deterministic reward calls. At 10,000 calls they ranked 16th of 25, where REINVENT ranked first on a prior trained on human data ([Gao et al. 2022](https://arxiv.org/abs/2206.12411)). Their one theoretical point in favour is that a Boltzmann response is stochastic fictitious play, which converges globally in zero-sum games ([Hofbauer & Sandholm 2002](https://www.econometricsociety.org/publications/econometrica/2002/11/01/global-convergence-stochastic-fictitious-play)).
- **A tempered population.** Noisy-Metropolis acceptance is exact under Gaussian noise ([Ceperley & Dewing 1999](https://arxiv.org/abs/physics/9812035)). But at 20 games a candidate the standard error of a difference is 0.158, so the proposed coldest tier would freeze; usable inverse temperatures are about 6-19.

None of the three is in the plan.

Nodes N6, N9; families H27-H35. Plan C23, C24, C25, C40, C41, C42.

## Noise is half the problem, and pairing buys less here than in poker

The simulation in the `--select-z` docstring shows the scale of the noise:

- With 3 candidates at about 10 games each, a null in which every candidate equals its deck still moves 73% of decks an iteration.
- With 1 candidate at z 1.0, the null moves about 15%, and a real +0.2 gain is taken only about 60% of the time.
- The top-12 distance has an A/A RMS of 2.0-4.8 cards, so gaps under about 5 cards between matched runs are noise (ledger).

The variance reducers are well measured:

- **Luck correction.** AIVAT cut the standard deviation of heads-up no-limit poker results from 25.96 to 8.10: "three times reduction in standard deviation allows us to achieve the same statistical significance with ten times less data" ([Burch et al. 2018](https://arxiv.org/abs/1612.06915)). Under greedy judging only the chance terms apply, which gave 33.8% in Leduc poker.
- **Shared randomness.** Shared pre-shuffled decks in Dominion MCTS were worth 25-40% more simulations ([Veness, Lanctot & Bowling 2011](https://proceedings.neurips.cc/paper_files/paper/2011/file/d736bb10d83a904aefc1d6ce93dc54b8-Paper.pdf)). Card-game AI competitions replay seeds with seats swapped ([Kowalski & Miernik 2023](https://arxiv.org/abs/2305.11814)).
- **An adaptive acceptance bar.** Pollack and Blair's backgammon hill-climber was competitive in 1 of 10 replications with a fixed acceptance schedule. It was competitive in all 10 when the bar rose whenever challengers won more than 15% of the time ([Pollack & Blair 1998](http://demo.cs.brandeis.edu/papers/bkg_ml.pdf)).

The project's structure limits the gain. The claim that twin games "play out identically until a changed card is reached" was marked wrong. Both seats see deck-level tokens (MY_UNSEEN, OPP_DECKLIST) from the first decision, and mulligans reshuffle. The only deal-level pairing in the log (#50) gave a correlation of 0.24-0.28, at the 0.3 kill line that every pairing proposal sets. #139's apparent 55% variance cut came mostly from shared matchups, not shared deals. Pairing on opponent and seat still helps.

Inside the search, both search codes re-deal the hidden cards separately for each option, so every comparison between options carries the deal's whole luck. Using one seed per world is a few lines of code, and a plausible cause of the 60-70% target disagreement in the failed expert-iteration runs. Re-measurement is the check: one Hearthstone study's best fitness of 0.0062 measured 0.063 when re-evaluated at 300 games ([de Mesentier Silva et al. 2019](https://arxiv.org/abs/1907.01623)).

Noise reduction is also a diagnostic. If accepted moves still drift toward the walls once the noise falls, the drift is bias.

Nodes N5, N12; families H24, H25, H62. C29 (a three-reseed A/A, Tier A) sets the noise floor. C03 (common-random-number search, Tier B) tests how much of the re-deal noise it removes. C26 (a paired re-test of proposals) is parked.

## Crossing from the walls to a tempo archetype needs coordinated moves that RL rarely finds alone

Going from the walls to Haymaker takes about 8-10 coordinated card changes, and the hybrids in between are probably worse than either end (analysis §1). No ledger family has tested this valley.

The nearest literature is Dominion, where Big Money plays the walls' role: many short decision sequences, and value that barely depends on skill. RL that optimises win rate learns Big Money, and "the only way to learn an Engine strategy is to avoid ever learning a Big Money strategy" ([Gerigk & Engels 2023](https://ojs.aaai.org/index.php/AIIDE/article/view/27518)). Their fix started 75% of training games from a mix that included a hand-built 12-card engine deck. The agent's decks became 60% Action cards, against Big Money's 15%. But it won only 14% against a Big Money bot, one of five seeds failed, and the run used reward shaping and a hand-written heuristic. That is style without strength, and the fix addressed buying, not play.

Search does not escape the attractor either: "search-based approaches ... also find Big Money strategies rather than Engines". A self-play buyer went 912-27-61 against Big Money, and 418-24-558 against an engine it had never explored ([Halawi et al. 2024](https://arxiv.org/abs/2405.06846)). Across about 1,000 kingdoms, Fisher found only about five without a dominating strategy, and noted that "interesting strategies will be skipped unless the algorithm is run for a very large number of generations" ([Fisher 2014](https://graphics.stanford.edu/~mdfisher/DominionAI.html)).

The board games that did rediscover human play passed through non-human stages. AlphaGo Zero used 4.9M games in 3 days, preferred a weak corner move at 10 hours, and learned ladders "much later" ([Silver et al. 2017](https://discovery.ucl.ac.uk/id/eprint/10045895/1/agz_unformatted_nature.pdf)). AlphaZero's seeds settled on different human opening lines: the Berlin in 92.8% and 88.9% of two runs, and 3...a6 in 89.2% and 85.8% of two others ([McGrath et al. 2021](https://arxiv.org/abs/2111.09259)). One run may therefore find one human archetype, not the human mix (effective number 3.6). The compute gap lies in search per move, not in games: the desktop plays about 1.44M games in 3 days, only 3.4 times fewer than AlphaGo Zero.

The pilot-side remedies are curricula over start states and practice levels:

- **Reverse curricula.** Keeping start states whose success lies in [0.1, 0.9] solved tasks where uniform starts reached about 10% and 2% ([Florensa et al. 2017](https://arxiv.org/abs/1707.05300)). Nothing in the project has started a PPO episode mid-game, and `Game.clone` already re-deals the hidden zones.
- **Never curate the deal.** On ground-truth black-ice racing, a curriculum over aleatoric parameters scored 543, against 581 for domain randomization and 616 for SAMPLR ([Jiang et al. 2022](https://arxiv.org/abs/2207.05219)).
- **Learnability scoring is defined only for deterministic levels.** Learnability sampling beat regret proxies, whose buffers filled with already-solved levels (learnability 0.01-0.02 against 0.22). But its stated scope is deterministic levels with binary outcomes ([Rutherford et al. 2024](https://arxiv.org/abs/2408.15099)); here p(1−p) peaks at mirrors and coin flips.
- **Learned antagonists are fragile.** PAIRED scored 26 against robust PLR's 531 on CarRacing ([Mediratta et al. 2023](https://arxiv.org/abs/2308.10797)), and a fixed antagonist stalls the curriculum at its own level ([Gur et al. 2021](https://arxiv.org/abs/2201.08896)). One-turn search is a free antagonist here: the regret sits on the fast-deck seat, while the walls' seat gains about nothing.

Nodes N2, N6, N9, N10; families H05-H12, H27, H28, H45, H46. C30, the pilot-first warm-up (Tier A), is the "never learn Big Money" arm and the plan's prevention start. C28, the valley test along edit paths (Tier B), is the first direct measurement of this link. C36 (branch starts), C18 (a separate best-response pilot against frozen walls) and C41 are parked. Search-regret curation and deal-conditioned learnability, both kept by the fact-check, have no plan id.

## A mis-specified game makes the collapse the right answer to the wrong question

"Task specification includes not only reward design, but also the choice of training environment", and specification gaming is "caused by misspecification of the intended task, rather than any flaw in the RL algorithm" ([Krakovna et al. 2020](https://deepmind.google/blog/specification-gaming-the-flip-side-of-ai-ingenuity/)). Inferring optimality from reference behaviour fails under a mis-specified environment: "none of the standard models are robust to a misspecified τ or γ" ([Skalse & Abate 2023](https://ar5iv.labs.arxiv.org/html/2212.03201)). Behaviour that looks suboptimal can be near-optimal under the dynamics the actor assumed ([Reddy, Dragan & Levine 2018](https://arxiv.org/abs/1805.08010)).

Benchmarks against humans therefore match the conditions of the human reference. AlphaStar played "under professionally approved conditions" ([Vinyals et al. 2019](https://deepmind.google/discover/blog/alphastar-grandmaster-level-in-starcraft-ii-using-multi-agent-reinforcement-learning/)). Maia dropped bullet games, and moves made with under 30 seconds left ([McIlroy-Young et al. 2020](https://ar5iv.labs.arxiv.org/html/2006.01855)). Evan's axiom that the human lists are optimal holds for the game they were built for. That game had 20-minute Swiss rounds, in which an unfinished game went to the player with more Prizes taken for 2 of 3 points, and a Prize tie gave 1 point each ([archived STS page](http://old.pokemonaaah.net/other/junk/sts/fossil.shtml); the year is inferred from the sets).

How a game ends shapes what wins:

- **A limit is either the real rule or a training device.** A limit that is part of the task should be the real rule, visible to the agent; a limit used only for training should bootstrap at the cut ([Pardo et al. 2018](https://arxiv.org/abs/1712.00378)). The plain draws of #140-143 are neither, and at 40 turns the share of games ending at the limit rose from 43% to 94%. `env/runner.js` also ends both the time draw and the 5,000-decision cap with reward 0 and no bootstrap. That is a cheap correctness fix, whatever the clock decision.
- **Punishing draws breeds new passivity.** A draw paid −1000 to both sides still left Sumo agents passive until a dense curriculum was added, and that curriculum is shaping ([Bansal et al. 2018](https://ar5iv.labs.arxiv.org/html/1710.03748)). Three points for a win raised goals and cut draws in football ([Moschini 2010](https://ideas.repec.org/p/isu/genres/12942.html)), but leading teams turn defensive ([Dilger & Geyer 2009](https://ideas.repec.org/a/sae/jospec/v10y2009i3p305-318.html)). A point for the overtime loser sent more games to overtime ([Franck & Theiler](https://econpapers.repec.org/RePEc:rsd:wpaper:0024)). Under a Prize-decided clock, expect a lead-then-stall attractor; the walls led on Prizes in 109 of their 148 deck-out wins (#141).
- **Scoring rules get exploited.** A pass-adversary beat no-search KataGo 99.9% of the time by exploiting how games are scored. It lost all 1,000 games against a victim defended at that rule, and lost to amateurs ([Wang et al. 2023](https://ar5iv.labs.arxiv.org/html/2211.00241)). Human players found a fatigue-stall deck in Hearthstone that wins before the game's 90-turn cap ([Kotaku 2017](https://kotaku.com/new-hearthstone-strategy-relies-on-running-out-the-cloc-1816209033)).
- **There are detectors for degenerate rules.** Restricted play flags games in which random play is "unreasonably effective" ([Jaffe et al. 2012](https://cdn.aaai.org/ojs/12513/12513-52-16035-1-2-20201228.pdf)), and a low completion rate marks a flawed game ([Browne & Maire 2010](https://eprints.qut.edu.au/31909/1/c31909.pdf)).

The project's numbers point at the clock and pilot strength together. Exact per-turn STS re-scoring of #139's greedy games gives the walls 0.482, 0.553, 0.620 and 0.665 of the points at cuts of 20, 40, 50 and 60 turns; the end-of-game Prize proxy had given 0.641-0.675 (plan §6, for log #150). One-turn search on both seats with draws at 50-60 turns gives the walls 0.44-0.46, but a greedy judge with a 60-turn draw still gives 0.60 (#147).

Because the walls' share rises monotonically with the cut, T alone sets the verdict. T must therefore be fixed in advance, drawn from a stated prior or reported as a curve, and never chosen by its effect on the distance to the lists. AlphaZero set its cap from the game's typical length ([Silver et al. 2017](https://ar5iv.labs.arxiv.org/html/1712.01815)).

Open decklists belong here too: the pilot sees the opponent's whole list, which a 2000 player lacked. Observational overfitting is documented ([Song et al. 2020](https://arxiv.org/abs/1912.02975)), but the link to stall plans is untested, and #73's hint that hiding the lists helped was corrected as noise (#74).

Nodes N1, N10; families H01-H04, H51-H54. In Tier A: C13 stage 1, C14 (draw-seeking check), C09 (open decklists), C02 (outside research) and the C33/C40 message to Evan. In Tier B: C35, the Prize margin as the pilot's terminal reward, a rule-2-compatible change of objective never tested. C01 and C15 are parked, and C34 (the round rule in training) needs Evan's go-ahead.

## The research loop collapsed like the population, and the same remedies apply

The research process shows the same failure pattern as the population:

- **No experiment could tell the explanations apart.** Each of the 27 screens records a single hypothesis string, and 19 reuse another screen's recipe. Their usual result, "relapses like the control", is predicted by every live explanation. "If an item of evidence seems consistent with all the hypotheses, it may have no diagnostic value at all" ([Heuer 1999](https://www.cia.gov/resources/csi/static/Pyschology-of-Intelligence-Analysis.pdf)), and "any conclusion that is not an exclusion is insecure and must be rechecked" ([Platt 1964](https://people.csail.mit.edu/ythomas/InterestingArticles/Strong_Inference.pdf)). The results that did move the explanation were cheap probes built to split hypotheses (#137, #139, #147).
- **One factor at a time missed the only positive interaction.** "Interactions are not estimable from OFAT experiments" ([Czitrom 1999](https://pdfcoffee.com/one-factor-at-a-time-pdf-free.html)). Turn limits (#143) and search judging (#146) were each rejected alone, yet together they gave 0.44-0.46 (#147).
- **Single seeds mislead.** Two 5-seed sets with identical settings differed at p = 0.0016 ([Henderson et al. 2018](https://ar5iv.labs.arxiv.org/html/1709.06560)), and 5 seeds carried a 51% type-II error in one example ([Colas et al. 2018](https://ar5iv.labs.arxiv.org/html/1806.08295)). Confidence sequences stay valid under the continuous peeking that screens get ([Ramdas et al. 2023](https://arxiv.org/html/2210.01948v2)).
- **Ideas repeat.** LLM idea generation kept 200 unique ideas out of 4,000 ([Si, Yang & Hashimoto 2024](https://arxiv.org/html/2409.04109)), which is why a mechanism-level ledger with near-duplicate rejection matters. The case for isolated research islands is less robust ([Rosenstock, Bruner & O'Connor 2017](https://cailinoconnor.com/wp-content/uploads/2015/03/In_Epistemic_Networks_Is_Less_Really_Mor-FINAL-VERSION.pdf)).
- **Effort piled up on a few nodes.** The ledger's critic finds 63% of 214 test rows on six nodes, with N8 at 6 rows and N9 at 7. Verification corrected 50 of 69 family statuses.
- **Delta debugging can isolate the judge's verdict flip.** Zeller's algorithm isolated one failure-inducing change among 178,000 ([Zeller 1999](https://www.cs.purdue.edu/homes/xyzhang/fall07/Papers/p253-zeller.pdf)). Its natural target is the gap between pilot-v2 (walls 0.26) and the population pilots (0.68-0.75). C07 reads it first with zero training, then C17's matched fine-tunes.

Node N12; families H42, H62-H66. The plan's own method applies these remedies:

- it ranks experiments by information per desktop-hour;
- it puts a prevention start among the first four screens;
- it allows at most 2 of 3 slots on the incumbent lineage;
- it puts C29 (the A/A) in Tier A.

C04 (recipe registry) and C05 (kill-horizon calibration, which is biased toward the screens that survived) are parked.

## When research outside the system is needed

Evan asked when to stop running internal variants and look outside the system: at the literature, at theory, or at the game's real-world context. The methodology angle gives five triggers, and the other angles give concrete tests that fire them. Go outside when any two triggers fire, or when T3 or T4 fires alone. Keep a small standing floor of outside work regardless, for two reasons:

- Adaptive processes, "by refining exploitation more rapidly than exploration, are likely to become effective in the short run but self-destructive in the long run" ([March 1991](https://arken.nmbu.no/~sigury/AOS_234/320_Pensum/March_91_Exploration%20and%20exploitation.pdf)).
- Exploration that stays inside the organisation has consistently lower impact ([Rosenkopf & Nerkar 2001](https://ideas.repec.org/a/bla/stratm/v22y2001i4p287-306.html)).

The thresholds (two triggers, catch-all weight 0.3, a 15-20% floor) are proposed starting values, and March also warns against too much exploration.

| Trigger | Fires when | Source | Status now |
|---|---|---|---|
| T1 Stall | Hypotheses excluded per desktop-day by internal work fall below the last outside round's yield | Charnov (secondary sources); [Weitzman 1979](https://www.econometricsociety.org/publications/econometrica/1979/05/01/optimal-search-best-alternative) | Fired in retrospect at #116 (16 pilot cards, competence unmoved) |
| T2 Degeneration | Changes patch the core without a corroborated novel prediction about type or shape | [Lakatos (SEP)](https://plato.stanford.edu/entries/lakatos/) | Fired in retrospect at #116; the "shape held, type not" run of #140-#147 fits it too |
| T3 Anomaly | A robust result falls outside every live hypothesis's band | [Kuhn (SEP)](https://plato.stanford.edu/entries/thomas-kuhn/) | Fired in retrospect across #127-#137; open anomalies A1-A9, e.g. A4: practice on the lists left the pilot 44 Elo behind pilot-v2 |
| T4 Exhaustion | The catch-all's weight passes about 0.3, or every named hypothesis has failed a prediction | [Heuer 1999](https://www.cia.gov/resources/csi/static/Pyschology-of-Intelligence-Analysis.pdf) | Not yet: several families lack a powered test |
| T5 Repetition | 2 of the last 5 proposals are mechanism-level near-duplicates | [Si et al. 2024](https://arxiv.org/html/2409.04109) | Fired in retrospect across #127-#137; the critic lists 12 repeated mechanisms |

Each angle supplies an exhaustion test for its own family:

- **Game theory.** The walls are a resolved Condorcet winner, or the only sink, over {walls, human archetypes, population types} under every affordable judge, search plus a draw limit included. Meta-level methods are then exhausted; research a stronger judge or the game's definition (C16).
- **Selection.** Non-wall decks are strictly Pareto-dominated on every panel case, with confidence intervals. The fact-check corrected the original form of this test, "only walls have positive lexicase selection probability", because that implication runs one way only.
- **Generators.** A null-reward head does not collapse (incoming entropy at least 2.5 at iteration 492), while a generator that keeps 3 or more types still sees every non-wall type at least 0.15 below the walls. The 0.15 is a proposed value; the lists already score 0.25-0.34 against the population (#131).
- **Search.** The strength ladder (greedy, one-turn, common random numbers with k8, nested level 2) plateaus with the walls at 0.55 or more in the clockless game. Play strength within reach is then not the lever, and the gap is the game's definition (C10, C13).
- **Curricula.** Either a pilot trained only on the fast seat cannot close the search gap in 8-10 iterations, which makes the learning rule the bottleneck. Or the curated levels stagnate on irreducible regret in long deck-out games, which would need belief-aware UED that no one has built.
- **Co-design.** Judge rank fidelity stays at Kendall tau 0.5 or below, or the fast-learner ratio stays above 1.1, at the largest affordable budget.
- **Card games.** Any of three conditions fires it:
  - three mechanism families give one signature (already met);
  - a diagnostic places the deciding variable in a capability the loop does not vary;
  - the nearest published successes needed 100 times the compute, measured in search per move rather than games.

The ledger's own trigger (S30) has fired: three or more mechanistically different interventions landed within twice the A/A RMS of a matched control, with the top-12 core cards unchanged. The critic warns that it rests on underpowered or confounded screens, so most families need one powered internal test first.

One question that no run can answer now blocks the leading hypothesis, E+P (#147): how many engine turns a 20-minute STS 2000 round allowed, how time was handled, and how stall decks fared. That is C02, about 5 agent-hours in Tier A, under two rules: the formula for T is written before any reading, and outside data on which decks won never sets a parameter.

Two more outside questions are conditional:

- If a powered search-only judge still keeps the walls, research how to evaluate designs without a co-adapted evaluator.
- If expert iteration v4 (C37) fails, research how to distil imperfect-information search into the pilot.

Do not go outside while a cheap, discriminating, untested experiment with written predictions is available (analysis §7). The first outside review's yield was modest: its diagnosis had already been re-derived internally, and its top pick failed alone (#146). Outside rounds pay best when aimed at a specific anomaly.

## What the literature does not cover, and where the evidence is thin

- **No direct precedent.** No card-game paper rebuilds a human metagame's deck composition from self-play. The quantitative rediscoveries are board games with strong search or huge compute; DeepNash used 768 learner and 256 actor TPU nodes ([Perolat et al. 2022](https://arxiv.org/abs/2206.15378)).
- **Deterministic sources.** Nearly every effect size comes from deterministic evaluation: program synthesis (lexicase), molecule oracles (diversity filters, GFlowNets), routing (Poppy), and mazes and robots (quality-diversity, curricula, co-design). Here a case is a Bernoulli game judged about 10 times. No source studies selection or generator dynamics under that noise, with an evaluator that learns alongside the population.
- **Empty searches.** The angles found no lexicase in competitive coevolution or game agents, no curriculum (UED) work on card games or decks, no deck generator trained on win/loss results against a co-learning opponent, and no measurement of how a deck style's payoff moves with search budget. Deal-conditioned learnability, search-regret curation and the paired-greedy control variate are the angles' own adaptations, untested anywhere.
- **Transfer gaps.** Coevolution evidence comes from abstract problems, and on the one realistic problem archives did no better than plain coevolution. Co-design studies have no competing, non-transitive designs. Mitchell's results are two-population host-parasite runs, with coexistence shown in one typical run.
- **Thin headline evidence.**
  - Strgar & Kriegman: 3 trials, no statistical test, one domain.
  - AdaControl, AV-AIVAT and GARIP: unreviewed preprints.
  - Juliani & Ash: on-policy plasticity loss significant only under one shift.
  - Bucci & Pollack: focusing shown in single qualitative runs.
  - The Dominion engine-start fix: style without strength.
- **Limits of the fact-check.** Several angles ran out of search budget. Lantz et al.'s strategy ladder, Silver & Tesauro's full tables, multi-fidelity Monte Carlo and studies of deck bias by agent strength were not verified, and nothing here rests on them. The nine claims found wrong are not used as evidence. Among them:
  - the Anytime PSRO monotonicity claim, which covers exact-Nash ADO only;
  - the Tales of Tribute "cycle", which was read in reverse;
  - the novelty of a moves-left head (#84 built one, and it lost 22.6 Elo in #88);
  - the claim that paired twin games stay identical until a changed card is drawn.
- **No literature thresholds.** Every numeric trigger here is a proposed starting value: a likelihood ratio of about 10, a catch-all weight of 0.3, a 15-20% floor, an early-to-final ρ of 0.7 and the 0.15 generator gap.

## How the ideas map onto the ledger and the plan

Under the cheaper spend Evan chose, Tier A (items 1-10, about 35 desktop-hours or 1.5 days) and Tier B (items 11-14, about 29 desktop-hours) run first. The conditional items 15-16 run only if their gates fire. The rest is parked, for cost, for missing prerequisites, or pending a decision by Evan.

| Idea (fact-check verdict) | Nodes | Families | Plan | Status |
|---|---|---|---|---|
| Zero-training judge zoo; delta-debug pilot-v2's verdict (keep) | N4, N9, N10 | H18, H20, H52 | C07; C17 | Tier A 2; conditional 16 |
| Exact STS rule on all 24 lists, strength ladder (keep, high) | N1, N2, N4 | H03, H05, H22 | C13 | Tier A 3 (stage 1) |
| Outside research on the specification (keep) | N1, N12 | H03, H61 | C02 | Tier A 8 |
| Draw-seeking check of the turn-limit runs | N1, N10 | H01, H04 | C14 | Tier A 7 |
| Open decklists (critic's gap) | N1, N11 | none | C09 | Tier A 1 |
| Null-reward drift test of the head (keep) | N6 | H30-H34 | C24; C25 | Tier A 9; conditional 15 |
| Composition-neutral base measure (keep, narrowed) | N6, N9 | H27 | C40; C23, C41 | Tier A 4 (ruling); parked |
| Pilot-first warm-up ("never learn Big Money") | N8, N9 | H45, H46 | C30 | Tier A 6 |
| A/A and run-level replication (keep, high) | N12 | H42, H62 | C29 | Tier A 5 |
| CRN and breadth over horizon in search (keep) | N2, N4 | H05, H11, H22 | C03 | Tier B 11 |
| Human-field tempo ladder and competence panel (strength-ladder idea, keep) | N2, N4 | H05, H19 | C10 | Tier B 12 |
| Prize margin as terminal reward (critic's top untested) | N10 | H29, H51, H54 | C35 | Tier B 13 |
| Valley test along edit paths (DOSSIER, Provincial) | N6, N7 | none | C28 | Tier B 14 |
| Empirical-game audit, human-free decision of record (keep, high) | N4, N5, N7 | H18, H22, H23 | C16 | Parked, cycle 2 |
| Searched verdict with paired greedy control variate (keep, high) | N4, N5 | H22, H23 | C20; C38 | Parked, after C03 |
| Reset-and-fine-tune judge (keep) | N4, N8 | H18, H20, H43 | C39 | Parked, gated on C17 |
| Leaf value for the judge's own policy (keep) | N4, N10 | H47, H50 | C12 | Parked |
| Paired candidate-vs-parent games, AIVAT (keep) | N5, N12 | H24, H25 | C26 | Parked |
| QRE allocation, torus, lexicase on measured matrices | N5, N7 | H39, H41 | C27; C32 | Parked |
| Local competition with league heads; hard cap | N7 | H37, H39 | C43; C44 | Parked |
| Best-of-K credit with distinct starts (keep) | N6 | H30 | C42 | Parked, gated on C24 |
| Branch starts, reverse curriculum (keep) | N2, N10 | H06, H11 | C36 | Parked |
| Separate best-response pilot (regret reducibility) | N3, N7 | H17, H19, H38 | C18 | Parked |
| Plasticity probe, policy held fixed (keep, high) | N3, N11 | H15, H56 | C22 | Parked |

Six ideas the fact-check kept have no plan id:

- anti-opportunistic acceptance against a held-out panel;
- shuffle-randomised per-card causal values, a diagnostic that costs no extra games;
- search-regret curation of practice games;
- deal-conditioned learnability;
- bootstrapping at the decision cap;
- ITER (iterated distillation into a fresh network), gated on C22.

Several ideas are left out on purpose: MMD and R-NaD magnets, NeuPL, diversity filters, GFlowNets, tempered populations, Dominated Novelty Search, minimal-criterion coevolution, CMA-MAE thresholds, MAESTRO, an ACCEL archive and mixtures of experts. Each overlaps a mechanism already tried, needs compute the desktop lacks, conflicts with rule 3, or lacks evidence at this noise level.

## Conclusion

The first review put the judge upstream of the drafter. This one shows why that order is forced and how to test it. Niches, lexicase, local competition, equilibrium scoring, best-of-K credit and curricula all act on what a payoff matrix already holds. Under the population pilot that matrix has a Condorcet winner, and within the human field its cycles are weak.

Tier A therefore spends the budget on four things:

- reading the matrix under several judges (C07, C13);
- separating drift from signal in the proposer (C24);
- measuring the noise floor (C29);
- checking the game's specification (C02, C14, C09).

It adds a prevention start (C30), so the cycle does not only test escape from wall states. The best-supported diversity machinery waits until some judge's matrix shows non-wall types that are not dominated. If no affordable judge ever shows them, the triggers place the remaining gap in the game's definition or in the learner, outside the meta level, and the next research round belongs there.
