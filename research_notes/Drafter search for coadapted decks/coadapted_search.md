# Search operators and signals for co-adapted components under noisy evaluation

Scope note: this pass used about 15 tool calls and about 17 cited sources. Several fetches returned only arXiv abstracts or search snippets; those are marked. Items from memory and not checked this session are marked "(memory, unverified)". No effect sizes from the linkage-learning or BO papers were available in the fetched text; where none is stated, it is listed under Gaps.

## Q1. Recombination and linkage: what crossover and linkage learning gain over mutation-only search under noise

### Takeaway
Linkage-learning GAs (DSMGA-II is the one checked) are reported to need fewer evaluations than hBOA and LT-GOMEA on trap, NK, Ising and MAX-SAT problems, but the abstract gives no numbers, and nothing this pass found compares crossover against mutation-only search under noise with numbers. Noise is handled mainly by resampling theory, which says resampling helps in some regimes and not others.

### Cited Findings
- DSMGA-II builds a dependency structure matrix from pairwise linkage tests, forms an incremental linkage set, and uses restricted mixing and back mixing. Benchmarks: concatenated, folded and cyclic trap; NK-landscapes; 2D Ising spin glass; MAX-SAT. Reported to outperform LT-GOMEA and hBOA "in terms of number of function evaluations"; no numbers in the abstract; no population sizes or budgets stated; no comparison with a mutation-only GA; noise not discussed in the abstract. [arXiv 1807.11669](https://arxiv.org/abs/1807.11669) (abstract only; fetched)
- A search snippet (not the full text) says DSMGA-II chose pairwise detection partly for its resistance to sampling noise. [arXiv 1807.11669](https://arxiv.org/pdf/1807.11669) (search summary, unverified in full text)
- Miller and Goldberg (1996) model how noise changes convergence under proportionate, tournament, (mu, lambda) and linear-ranking selection. Their population sizes were chosen with a conservative predictor. [Evolutionary Computation 4(2):113-131, abstract via Bohrium](https://www.bohrium.com/paper-details/genetic-algorithms-selection-schemes-and-the-varying-effects-of-noise/811933076908146689-2689); critique: [Rattray and Shapiro, core.ac.uk](https://core.ac.uk/download/78877694.pdf) states that under weak selection, Gaussian noise effects can be removed by enlarging the population.
- Goldberg, Deb and Clark's sizing relation includes selection noise, operator noise and objective noise, and was a conservative predictor on five test functions. (search summary; no URL retrieved; memory of the 1992 paper, unverified)
- Resampling theory: fixed resampling counts can give convergence with log-linear rates when noise variance shrinks near the optimum [Cauwet, core.ac.uk](https://core.ac.uk/download/49651762.pdf); growing or polynomially growing adaptive counts can work [same source]; resampling reduces noise standard deviation roughly with the square root of repeats [Liu, Saint-Pierre and Teytaud, core.ac.uk](https://core.ac.uk/download/49648739.pdf); adaptive sampling can beat fixed sampling when sampling fails [Qian et al., arXiv 1810.05045](https://arxiv.org/pdf/1810.05045).
- Conflicting results on Noisy OneMax: one analysis found resampling useless, another that the optimal resampling rate rises with dimension. Liu and Perez-Liebana also argue that first-hitting-time evaluation can distort the measured performance of noisy algorithms. [arXiv 1706.05086](https://ar5iv.arxiv.org/html/1706.05086)
- Compact GA gene-pool recombination is reported to "smooth" noise on OneMax. (search snippet; source not retrieved)
- Crossover in card-deck GAs: the Hearthstone and MTG sources found agree that naive crossover breaks colour and mana consistency, so repair or colour-aware operators matter. [Torino, Garcia-Sanchez et al., 2018](https://iris.polito.it/bitstream/11583/2706329/1/2018-kbsys.pdf) (search summary); [Active-genes Arena deckbuilding, arXiv 2001.01326](https://arxiv.org/pdf/2001.01326) (search summary: crossover and mutation restricted to "active" genes; baseline uniform crossover with constant mutation rate; not fetched).
- Hearthstone: Garcia-Sanchez et al. add a heuristic mutation operator, based on how human players modify decks, because the search space is large. This is a human-derived operator, so it would be ruled out by our no-human-priors rule in training. [Torino, 2018](https://iris.polito.it/bitstream/11583/2706329/1/2018-kbsys.pdf) (search summary)
- MTG: an NTNU master's thesis (2017) uses a GA for card selection, evaluated by expert analysis, not by play. [NTNU](https://ntnuopen.ntnu.no/ntnu-xmlui/handle/11250/2462429) (search summary). No MTG head-to-head of crossover vs mutation was found.

### Inferences
- No source found gives a crossover-vs-mutation comparison for deck building with numbers. Our own loop is therefore the first test we can design, and it should use a mutation-only control.
- Our selection (about 10 paired games a move) is far below the sampling needed for stable comparisons. My arithmetic, estimate only: for win/loss outcomes at p = 0.5, the standard error of a 10-game mean is about 0.5/sqrt(10) = 0.16, and about 0.045 at 125 games, before any paired-design variance reduction. Compare any recombination effect against that band.
- The simplest crossover that keeps multisets valid: for two parents, take each card-name's count from one parent, and repair to 60 cards and the 4-copy cap. A block variant copies whole Pokemon lines (Pokemon plus its Energy) from one parent. Both need the repair step the sources warn about.

### Gaps
- No effect sizes or evaluation budgets for DSMGA-II, LT-GOMEA, hBOA, P3, LTGA or royal-road results were in fetched text. The full DSMGA-II paper (arxiv.org/html/1807.11669v1) would give tables; not read this pass.
- No noisy-fitness benchmark for GOMEA-family methods was found. A 2024 parameterless GOMEA paper (Bosman et al., Evolutionary Computation) and Liao's 2019 thesis on optimal-mixing population sizing were seen in search results only; noise handling not confirmed.
- Royal road and building-block results (Mitchell, Forrest and Holland 1992 and later) are from memory (memory, unverified), not read here.

## Q2. Learned set-level proposals: which components belong together

### Takeaway
The learned-model route is best supported by BOCS-style surrogates with pairwise binary terms. BOCS was reported to beat combinatorial and BO baselines, but the sources checked give no evaluation counts or effect sizes, and no source checked tests it on noisy win/loss outcomes.

### Cited Findings
- BOCS fits a second-order binary model (linear plus pairwise terms) with a horseshoe prior, uses Thompson sampling, and optimises the acquisition with a semidefinite program. The abstract says it "consistently outperforms other methods from combinatorial and Bayesian optimization", with no specifics. [Baptista and Poloczek, ICML 2018, arXiv 1806.08838](https://arxiv.org/abs/1806.08838) (abstract only; fetched)
- Deshwal et al. (scalable BOCS) use the same second-order horseshoe model; categorical variables are one-hot encoded, which "can lead to a large number of binary variables". Benchmarks: binary quadratic programming, contamination, sparsification of zero-field Ising models, and low auto-correlation binary sequences. Results averaged over 10 random runs. The paper compares BOCS-SDP with BOCS-PSR only, and reports no numbers against COMBO or GAs. Evaluation counts are not stated. [arXiv 2008.08177](https://ar5iv.labs.arxiv.org/html/2008.08177) (fetched)
- The Deshwal paper cites prior work that COMBO "was shown to achieve better performance than BOCS for complex domains". This is their citation of others, not a result they measured. [same source]
- A search summary says BOCS scales poorly with many binary or categorical variables. [same source]
- Our 277-card pool one-hot encoded is a large binary space, which is the regime these sources flag as costly.

### Inferences
- A pairwise-term surrogate (card A and card B co-occur, with a horseshoe-like shrinkage) is the cheapest learned "which belong together" model in this set. It needs no human decks. It could be fit to the population's own top decks, as a proposal prior over group changes.
- Whether it works with noisy win/loss is untested in these sources. In our loop the surrogate would see about 125 paired games per decision, so it would need a strong prior, which is the open question.

### Gaps
- No evaluation counts, initial sample sizes or effect sizes for BOCS or COMBO in the fetched text.
- No GFlowNet, set-generator or EDA-with-pairwise-terms source was checked this pass; those are not covered here.
- No source found that runs any of these with a noisy win/loss objective.

## Q3. Large-step moves, consolidation, and game-agnostic agent-play signals

### Takeaway
Little was found this pass. The one relevant structural fact is that our "group change" (swap all copies of one card) is already a large-step move. Sources on macro-mutations and consolidation moves were not reached within budget, and I did not search the game-agnostic agent-play signals directly.

### Cited Findings
- Pidgeon (2025), a Hearthstone GA study of mutation and fitness-function parameters, reports that some fitness functions yield better decks than others; the playstyles of frequently used cards differ between fitness functions. Only the abstract was seen. [Pidgeon, pats.cs.cf.ac.uk](https://pats.cs.cf.ac.uk/!archive_desc?p=1321). It does not report a crossover-vs-mutation comparison in the abstract.
- "Evolving the Hearthstone Meta" (arXiv 1907.01623) evolves card attributes toward equal win rates, not decks; its operators are two-point crossover at 35%, mutation at 20%, and 5% per-gene change (search summary; the PDF fetch failed). [arXiv 1907.01623](https://arxiv.org/pdf/1907.01623)
- Garcia-Sanchez et al. report an AI-played playtest of EA-built decks against human-designed decks, with the human-derived mutation noted above. [Torino 2018](https://iris.polito.it/bitstream/11583/2706329/1/2018-kbsys.pdf) (search summary)
- Agent-play signals (dead-card rate, unused resources, legal-option counts, play against a passive opponent): not found in any source this pass. Judged "little or nothing" from this search, not from a full literature check.

### Inferences
- A consolidation move (for example, a move that reduces the number of distinct Pokemon names or Energy types) is the direct counter to the measured overspread (6.6 names vs 4.6; 3.7 Energy types vs 1.8). It would be a game-specific shape prior if it hard-codes Energy counts, so it should be stated as a count constraint learned or scored by the agent's own selection, not built in.
- A compound move that swaps a whole Pokemon line plus its Energy is a variable-depth move of the same kind. Both need the noise-aware acceptance rule from Q1.

### Gaps
- No macro-mutation or consolidation result was checked. Variable-depth and consolidation results from combinatorial design (for example Kernighan-Lin style variable-depth search) are from memory (memory, unverified).
- No check on game-agnostic agent-play signals as deck-building guidance; this is the main gap.

## Source list (checked this pass)
- arXiv 1807.11669 (DSMGA-II abstract): https://arxiv.org/abs/1807.11669
- arXiv 1806.08838 (BOCS abstract): https://arxiv.org/abs/1806.08838
- arXiv 2008.08177 (scalable BOCS, full text): https://ar5iv.labs.arxiv.org/html/2008.08177
- arXiv 1907.01623 (Evolving the Hearthstone Meta, search summary only): https://arxiv.org/pdf/1907.01623
- arXiv 2001.01326 (Active genes Arena, search summary only): https://arxiv.org/pdf/2001.01326
- arXiv 1810.05045 (Qian et al., adaptive sampling, search summary): https://arxiv.org/pdf/1810.05045
- arXiv 1706.05086 (Liu and Perez-Liebana, noisy evaluation): https://ar5iv.arxiv.org/html/1706.05086
- arXiv 1806.08547 (EA runtime in dynamic and stochastic settings, search summary): https://arxiv.org/pdf/1806.08547
- Cauwet fixed resampling: https://core.ac.uk/download/49651762.pdf (search summary)
- Liu, Saint-Pierre, Teytaud resampling: https://core.ac.uk/download/49648739.pdf (search summary)
- Astete-Morales, Liu, Teytaud: https://core.ac.uk/download/49468134.pdf (search summary)
- Rattray and Shapiro: https://core.ac.uk/download/78877694.pdf (search summary)
- Miller and Goldberg 1996 (abstract): https://www.bohrium.com/paper-details/genetic-algorithms-selection-schemes-and-the-varying-effects-of-noise/811933076908146689-2689
- Garcia-Sanchez et al. 2018 Torino: https://iris.polito.it/bitstream/11583/2706329/1/2018-kbsys.pdf
- Pidgeon 2025: https://pats.cs.cf.ac.uk/!archive_desc?p=1321
- NTNU MTG GA thesis 2017: https://ntnuopen.ntnu.no/ntnu-xmlui/handle/11250/2462429

## Next searches (not yet run)
1. Full DSMGA-II text (arxiv.org/html/1807.11669v1): effect sizes, budgets, population sizes.
2. Noisy-fitness GOMEA or linkage-learning papers (search for stochastic fitness, partial evaluation).
3. Macro-mutation and consolidation moves in set-cover or combinatorial design.
4. GFlowNet and set-generator papers that learn co-occurrence from their own samples, with noisy-reward experiments.
5. Agent-play signals (dead-card rate, legal-option counts) in automated game design.
