# Exploration-exploitation for combinatorial deck design under very noisy evaluation

Tags: **[read]** = page fetched and checked; **[snippet]** = search-result text only, not opened in full; **[memory]** = my own arithmetic or background knowledge, unsourced here. Budget used: about 12 tool calls. The Audibert et al. (COLT 2010) PDF could not be decoded, so nothing in it is verified.

## 1. Best-arm identification and racing under noise

### Takeaway
Fixed-budget methods (successive halving, Hyperband) and racing (F-race, irace) are built to discard weak candidates early. They can only find effects that the per-candidate sample supports. With about 10 games per move and per-card effects near 0.01 of a game, no racing schedule can resolve single moves, so the design has to pool information across decks.

### Cited Findings
- Hyperband is a fixed-budget bandit method. It is random search with adaptive resource allocation and early stopping, and it calls successive halving as a subroutine. Its abstract reports "over an order-of-magnitude speedup" against Bayesian-optimization competitors on deep-learning and kernel problems; it gives no separate figure against random search. [read: https://arxiv.org/abs/1603.06560]
- Successive halving keeps the top 1/η of arms and repeats until one remains. Hyperband runs several brackets that trade the number of starting configurations against budget per configuration, under a fixed total budget. [snippet: https://arxiv.org/pdf/2105.13059; https://arxiv.org/pdf/2302.00511]
- Successive halving was proposed for stochastic best-arm identification in 2013 and reanalysed for the non-stochastic setting in 2016. [snippet: https://www.envisioning.com/vocab/successive-halving]
- Successive rejects is parameter-free. UCB-E needs an exploration parameter that depends on the unknown task hardness, and its performance is sensitive to that parameter. [snippet: https://www.learningtheory.org/colt2010/papers/59Audibert.pdf, the search page was for the same paper; the PDF itself did not decode]
- LUCB samples both the current best and the second-best arm, and stops when the best arm's lower bound exceeds the second-best arm's upper bound. [snippet: https://homes.cs.washington.edu/~jamieson/resources/bestArmSurvey.pdf]
- F-race compares candidates block by block using the Friedman rank test, and drops candidates once the evidence against them is strong. Its descendants are Sampling F-race, iterated F-race (which resamples new candidates around the current winner) and irace (which adds an elitist set and soft restarts). Course notes say it suits small configuration spaces. [snippet: https://arxiv.org/pdf/2202.01651; https://cw.fel.cvut.cz/b191/_media/courses/a0m33eoa/prednasky/frace.pdf]

### Inferences
- **Sample budget is the binding constraint.** [memory] For binary game outcomes with per-game SD about 0.5, a paired-difference SD near 0.7 and a 95% test, resolving a per-card effect of 0.01 needs roughly (2×0.7/0.01)² ≈ 20,000 paired games per move. That is about 2,000 times the 10 games used now. Racing can cut games on clearly bad moves, but it cannot make small effects visible at 10 games. The estimate is my arithmetic, not a measured result.
- [memory] The 1 SE keep rule with 10 games passes about 16% of truly null moves by chance (one-sided). That matches the observed 15% move rate, so most accepted moves are probably noise.
- **Implication for this project:** racing is useful only for early elimination of clearly bad moves (for example, cutting a move after 2–3 games when it is far behind). Resolving the small per-card effects needs a shared model across decks and iterations, such as a regression of win rate on card counts, not a separate test per move.

### Gaps
- No source found on racing in games with a paired design, where the noise is the matchup rather than the seed.
- The actual COLT 2010 successive-rejects bounds could not be checked.

## 2. Thompson sampling and Bayesian optimization over combinatorial spaces

### Takeaway
BOCS fits a sparse linear-plus-pairwise model over binary variables and uses Thompson sampling. This is the closest published method to a shared per-card model. Its pairwise term scales poorly for a few hundred cards, so a first-order model is the realistic version. Posterior variance gives rare cards natural optimism, but I found no source that tests this for rare components.

### Cited Findings
- BOCS uses a linear model over binary variables with pairwise interaction terms, a horseshoe prior on the coefficients, and Thompson sampling. It solves the acquisition step as a binary quadratic program using semidefinite programming. The authors report it beats other combinatorial and Bayesian methods with little data. [snippet: https://arxiv.org/pdf/1806.08838]
- A second-order model has Θ(d²) coefficients, which gives high-variance estimates when data is scarce. BOCS scales poorly with many binary or one-hot categorical variables. COMBO was reported to do better where higher-order interactions matter. [snippet: https://arxiv.org/pdf/2008.08177]
- Combinatorial Thompson sampling has a distribution-dependent regret bound of O(m log T / Δmin) for general combinatorial bandits. An approximate offline oracle breaks TS even in the single-arm case. [snippet: https://mlanthology.org/icml/2018/wang2018icml-thompson]
- A talk abstract proposes coupling base-arm posterior samples through one shared seed. This is claimed to induce coordinated optimism across arms. It is not peer-reviewed, and I did not open it. [snippet: https://econcs.sufe.edu.cn/16/25/c12812a267813/page.htm]

### Inferences
- **Proposal-side mechanism, no human priors.** [memory] A first-order Bayesian linear model over card presence (one coefficient per card, plus a noise model fed by all decks) gives each rare card a wide posterior. Thompson draws then propose it at a rate set by its uncertainty, not by a hand-set floor. Drawing one posterior sample per iteration and proposing its best swap is cheap, and needs no pairwise terms.
- The 2–4% proposal rate for rare cards is what a count-weighted head would give. [memory] A Thompson-style head would give rare cards a rate set by posterior width, which can be checked against the current 2–4%.

### Gaps
- No source on TS or BOCS-style methods applied to rarely-present components in a noisy game setting.
- No source on the coupled-seed method beyond the talk abstract.

## 3. Noisy evolutionary optimization: resampling, selection and drift

### Takeaway
A survey of noisy evolutionary methods lists resampling as the standard fix. Resampling can speed up the search exponentially in some theory cases, but it raises cost per candidate. Drift from noisy acceptance is a known concern, and I found no source that measures it for a threshold rule like the 1 SE keep.

### Cited Findings
- Rakshit, Konar and Das (2017) survey noisy evolutionary methods in five groups: fitness sampling, fitness estimation, dynamic population sizing, adapting the search, and modifying selection. Resampling is the average of k evaluations, which improves accuracy at higher cost. [snippet: https://digitalcommons.isical.ac.in/journal-articles/2624]
- Qian et al. (2018, Evolutionary Computation) give a running-time analysis where sampling can speed up noisy evolutionary optimization exponentially. [snippet: search result, no URL opened]
- Fieldsend (EMO 2015) studies accumulative resampling of elite members and adaptive re-evaluation. [snippet: https://ore.exeter.ac.uk/repository/bitstream/10871/17039/1/EMO_2015_final_version_fieldsend.pdf]
- Astete-Morales, Liu and Teytaud give log-log convergence for noisy optimization with polynomial resampling. [snippet: search result]

### Inferences
- **Re-evaluate the elite, not every move.** [memory] Under a fixed game budget, a move that passes the 1 SE rule once should be re-tested on fresh games before it is kept. This is the adaptive re-evaluation idea from Fieldsend, applied to the keep decision. It stops false positives from accumulating in the population.
- **Threshold drift.** [memory] A keep rule at 1 SE accepts noise moves steadily, so the population drifts toward whatever the noise favours. A higher threshold or a re-test removes this at the cost of fewer accepted moves.

### Gaps
- No source found that measures drift from a noisy keep threshold in a population of decks.
- The Qian et al. and Astete-Morales results were not opened, so I have not checked their assumptions.

## 4. Card-game deckbuilding with evolutionary search and evaluators

### Takeaway
Hearthstone deckbuilding work uses evolutionary search with a game simulator, scoring each deck against fixed opponent decks. Reported evaluation budgets are large (200 games per deck in one GECCO 2022 paper). Most of this literature does not use racing. Whether it helps this project depends on its budget, which is far smaller.

### Cited Findings
- García-Sánchez et al. (IEEE CIG 2016) use a genetic algorithm where each candidate deck is scored by a simulator playing against human-made decks. A 2018 journal version extends this to all nine heroes and adds a heuristic mutation operator. [snippet: https://www.scitepress.org/Papers/2023/117839/117839.pdf; https://iris.polito.it/bitstream/11583/2706329/1/2018-kbsys.pdf]
- Bhatt et al. (2018, "Exploring the Hearthstone deck space") use evolution strategies and report transitivity: evolved decks beat starter decks, and twice-evolved decks beat once-evolved decks. [snippet: https://digitalcommons.njit.edu/fac_pubs/8454]
- Deep Surrogate Assisted MAP-Elites (GECCO 2022) plays 200 games per deck and adds neural surrogates to cut that cost. MAP-Elites is out of scope for this round; I note it only as a budget reference. [snippet: https://ar5iv.labs.arxiv.org/html/2112.03534]
- "Evolving the Hearthstone Meta" (arXiv 1907.01623) searches for minimal card changes that move win rates toward 50%. Aggregator pages claim efficiency gains of 25% and 30%; these look auto-generated and unverified, so I did not use them. [snippet: https://arxivlens.com/PaperView/Details/evolving-the-hearthstone-meta-5918-2211659]

### Inferences
- The 200-games-per-deck budget is about 20 times the project's 10 games per move. Those methods rely on a fixed opponent set and a simulator, which matches this project's paired design.
- [memory] Surrogate-assisted search (a model trained on past decks to predict results) is the published answer to the same budget problem, and fits the pooling idea in section 1.

### Gaps
- No source on LOCM deckbuilding was searched in this round.
- No source gave a keep rule or selection rule that was tested against noise at this budget.

## 5. Proposal-side exploration for a learned proposer

### Takeaway
I found no source on exploration for a learned proposer over card components, so this section rests on memory and needs sourcing before it is used.

### Cited Findings
- None found. The searches returned nothing on entropy floors, count bonuses or novelty over components for a REINFORCE-trained proposer.

### Inferences
- [memory] Three options fit the stated constraint (no hand-picked cards): (a) a count-based bonus on each card's proposal rate, (b) an entropy floor on the head's distribution over cards, and (c) Thompson draws from the per-card posterior in section 2. Option (c) has the most principled link to the noise model; (a) and (b) are simple to add to the current REINFORCE loss.

### Gaps
- Needs a targeted search on REINFORCE with entropy regularization or count bonuses over discrete actions before this is recommended.

## Summary of what to test first (inferences, not results)
1. [memory] Pool per-card effects across decks with a first-order model and use its posterior to propose swaps (sections 1–2). This needs no change to the game budget.
2. [memory] Re-test any move that passes the 1 SE rule on fresh games before keeping it (section 3).
3. [memory] Use racing only to stop clearly bad moves early (section 1).
