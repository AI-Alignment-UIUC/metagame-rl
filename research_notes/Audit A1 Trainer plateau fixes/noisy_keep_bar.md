# Keep/confirm rules for a noisy 5-minute RL loop (M sd ~0.01, wanted effect +0.01 to +0.02)

Local numbers used below come from ar/results.tsv (22 rows) and notes/audits.md A1. "Inference" lines are my own arithmetic or reasoning, not from a source. Web research was about 14 calls; several primary papers could not be read in full (see Gaps).

## 1. What is the real noise? (A/A sd 0.0018 vs rerun spread 0.007-0.019)

### Takeaway
The 3-seed A/A sd of 0.0018 is almost certainly a lucky low estimate: an sd from 3 samples has only 2 degrees of freedom and a 95% upper bound about 6x the point estimate. Pooling the seed-1/seed-2 pairs of the three failed confirms gives sd ~0.0115 per run, so delta=0.01 is about 1 sd of a single run, not 5 sd.

### Cited Findings
- Colas et al. say to use at least n=20 samples in a pilot to estimate standard deviations, and to pick N larger than the power analysis says, because underestimated SDs give too-small N (their sim: N=17 needed with true SDs, only N=7 if SDs underestimated by 0.40) — [Colas, Sigaud, Oudeyer 2018 (ar5iv)](https://ar5iv.labs.arxiv.org/html/1806.08295)
- Same paper: at N=5 a worked example had beta=0.51 (51% chance of missing the effect); N=10 gave beta=0.19. Welch t-test preferred over bootstrap; bootstrap false-positive rate ~10% at small N against nominal 5%, and should not be used with fewer than 20 samples. Use alpha below 0.05 and correct for multiple comparisons — [same](https://ar5iv.labs.arxiv.org/html/1806.08295)
- Henderson et al. stress that RL variance across trials and seeds is high, many seeds are needed, and significance testing is needed because a higher mean can mislead; they used five fixed seeds — [Henderson et al. 2018](https://arxiv.org/pdf/1709.06560), [search summary](https://ar5iv.labs.arxiv.org/html/1709.06560)
- Patterson et al. note that long-tailed results violate Student-t assumptions, the percentile bootstrap fails with too few samples, and skewed agents need more runs — [Patterson et al. 2023](https://arxiv.org/pdf/2304.01315) (from search snippets only)
- Agarwal et al. argue point estimates from a few runs hide uncertainty; report interval estimates (stratified bootstrap) and probability of improvement — [Agarwal et al. 2021](https://arxiv.org/pdf/2108.13264)
- An aerospace autoresearch-agent paper proposes measuring seed noise on a fixed baseline across several seeds and using that sd as the unit for crediting gains — [arXiv 2606.20394](https://arxiv.org/pdf/2606.20394) (snippet only, not read in full)

### Inferences
- Local arithmetic (results.tsv): the three baseline M values are 0.4701/0.4665/0.4690 (sd 0.0018). Seed-1 vs seed-2 pairs of the same commit differ by 0.0065 (LAM 0.8), 0.0193 (curriculum), 0.0194 (frozen anchor). Pooled sd = sqrt(mean(d^2)/2) = ~0.0115 (3 df). A chi-square interval on the 3-seed sd (2 df) runs from ~0.5x to ~6x, so ~0.0009-0.011: the two estimates are compatible, and the larger one is the better-supported.
- Binomial floor: with ~4,500 games, sd of a share near 0.47 is ~0.0075 if every game were decisive and independent. So evaluation-game sampling alone explains most of a ~0.01 sd; the rest (~0.006) would be training variance. This split is a hypothesis; it can be tested by re-scoring one checkpoint twice (see Loop change 1).
- Winner's curse: the confirms were triggered by the highest seed-1 values (0.4815, 0.4829, 0.4917) and all regressed at seed 2 (0.4750, 0.4636, 0.4723). That is the pattern expected when gaps of ~1 sd are selected; it is not evidence of fragile effects.
- Wall-clock budget is a second noise source: train_s is fixed (~5 min) but games per run vary 2,801-7,413 for similar recipes and 3,257 vs 3,835 for the same commit (rows 16-17). Contention among workers and the GPU changes how much training a run gets. A fixed-iteration budget would remove this.

### Gaps
- Whether same-seed reruns of the same commit are bit-identical was not tested; I found no source for how nondeterministic PyTorch + multi-process rollouts typically are. Cheap local test below.

Loop change 1: (a) run baseline seed 1 twice and re-score one saved checkpoint twice with different eval seeds, to split eval variance from training variance and to check determinism. Cost ~10-15 GPU-min. Changes nothing in rules; respects self-discovery, game-agnostic, simple. (b) Replace "A/A sd of 3 seeds" with a pooled sd over all baseline and rerun pairs (currently ~0.011) and set the keep bar from it. Cost 0. Respects all rules.

## 2. How Fishtest/OpenBench handle small patches, and what it implies for M

### Takeaway
Fishtest decides with a sequential test (SPRT) against pre-chosen bounds, on paired games scored as a pentanomial, so it stops early on clear cases and spends games only where the evidence is ambiguous. The transferable pieces are pairing (common deals) and a sequential stopping rule with explicit alpha/beta, not a fixed delta on one seed.

### Cited Findings
- SPRT takes elo0 (null), elo1 (alternative), alpha and beta; these fix two log-likelihood-ratio bounds and the test runs until the LLR crosses one. Stockfish STC gainer bounds [0, 2] Elo and non-regression [-1.75, 0.25]; LTC gainer [0.5, 2.5]. Bounds trade expected games against the smallest gain worth passing — [Chessprogramming wiki, SPRT](https://www.chessprogramming.org/Sequential_Probability_Ratio_Test)
- The pentanomial model scores paired (colour-reversed, same opening) games as five outcomes. The trinomial model overestimates Elo confidence intervals, attributed to opening-book bias in both mean and spread. In the README's example (elo1=10) pentanomial passes with 1,809 expected games vs 2,191 for trinomial (~17-20% fewer) — [vdbergh/pentanomial](https://github.com/vdbergh/pentanomial)
- Fishtest's test is a generalised SPRT on the pentanomial model — [vdbergh/simul (via search)](https://github-redirect.dependabot.com/vdbergh/simul)
- Normalised Elo = logistic Elo / sqrt(1 - draw ratio) for a balanced book; it removes the draw-rate dependence of the sd — [vdbergh summary via search](https://github-redirect.dependabot.com/vdbergh/pentanomial)

### Inferences
- M already has the structure of a paired test: the same deck is played against its own copy. If candidate and baseline pilots are scored on identical deals, identical Trainer-to-Energy copies and identical coin flips (common random numbers), the opening/deal variance cancels in the difference, as pairing does in Fishtest. The Fishtest gain from pairing is modest in their own example (~17-20% fewer games), so do not expect more than ~1.2x from this alone; the larger win is the sequential rule.
- SPRT arithmetic for M-differences (my calculation): treat the candidate-minus-baseline difference d of paired runs as normal with sd sigma_d = 0.0115*sqrt2 = 0.0163 (use 0.014 at sd 0.010). Test H0: gain 0 vs H1: gain +0.015, alpha 0.05, beta 0.2. The per-pair LLR increment is mu1*(d - mu1/2)/sigma_d^2; expected +0.42 under H1 and -0.42 under H0 (with 0.0163). Bounds ln(16)=2.77 and ln(0.21)=-1.56 give expected ~6.6 pairs under H1 and ~3.7 under H0, about 13 and 7 runs. That is 35-65 GPU-min per candidate (5 min/run); a fixed 6-vs-6 design costs 60 min, so the sequential saving is real only when most candidates are null (as they are here: 0/17).
- With 17+ candidates tested, alpha 0.05 gives ~1 false keep per 20 tries; since prior of a real gain is low, use alpha ~0.01 for the final keep and a cheap screen before it.

### Gaps
- I did not find a published SPRT for a continuous, non-game metric with small n like this; the calculation above is textbook Wald, unverified against the loop.
- OpenBench documentation was not retrieved.

Loop change 2: replace "seed 1 > best + 0.01, then one seed 2" with a paired sequential confirm: for a candidate that passes a loose screen (seed-1 M > baseline-seed-1 M + ~0.5 sd), run alternating candidate/baseline runs (same seed indices, same eval deals) and stop at the LLR bounds above, capped at 6 pairs. Cost: expected ~25-50 GPU-min per screened candidate, cap 60. Edit is in fixed.py's `--confirm` logic (needs a new `--setup/--calibrate` per CLAUDE.md). Respects all rules (no human data used; game-agnostic; modest code).

## 3. Racing, successive halving, multi-fidelity: seeds vs budget, and low-fidelity proxies

### Takeaway
All of these allocate more evaluations to configurations that survive a noisy early cut. They help only when the low-fidelity ranking correlates with the target, and the ar/ loop is itself already the lowest fidelity (5 min), so using them means going up in fidelity for a few finalists rather than down.

### Cited Findings
- F-Race: run a rank-based Friedman test across configurations on all instances so far; if significant, compare each against the best with pairwise t-tests and drop those significantly worse. It suits few parameters — [F-Race lecture slides (CTU)](https://cw.fel.cvut.cz/b191/_media/courses/a0m33eoa/prednasky/frace.pdf)
- irace is an extension of iterated F-race for automatic configuration; current CRAN lists 4.4.3 (2026-04-23) on one mirror, 4.3 on others — [CRAN irace](https://cloud.r-project.org/web/packages/irace/index.html), [irace guide](https://mirror.linux.duke.edu/cran/web/packages/irace/vignettes/irace-package.pdf)
- ASHA samples configs at low fidelity and promotes the most promising to higher fidelity — [Orion docs](https://orion.readthedocs.io/en/v0.2.6/_modules/orion/algo/asha.html)
- Low-fidelity metrics (lower budgets in Hyperband) are presumably less convincing than high-fidelity ones; Hyperband loops a fixed sequence of successive-halving subroutines, and BOHB fits its surrogate only on the highest fidelity — [arXiv 2402.13641](https://arxiv.org/html/2402.13641v1)
- Short-horizon bias: meta-optimisation with short unrolls picks learning rates too small by orders of magnitude, even at 100 steps, on a noisy quadratic — [Wu, Ren, Liao, Grosse 2018](https://www.cs.toronto.edu/~mren/research/metaoptim/index.html)

### Inferences
- Wu et al. is a direct warning for LR/step-size rows in ar/: a 5-minute score rewards changes that help early (greedy) and punishes changes whose benefit shows later. Row 20 (LR x6, M -0.015) is the kind of result that could be short-horizon bias or true harm; the loop cannot tell which.
- Racing structure applies across candidates, not within the 5-minute run: screen cheaply, then give the survivors paired seeds. This matches Loop change 2 and 3.
- If low-fidelity rank correlation is unknown, the oracle control (practice on the evaluation decks, +0.015 over baseline per the audit) is the only anchor for "a real effect looks like this". +0.015 is about 1.3 pooled sd, so a single run detects it with power ~25-30% at alpha .05 (my estimate).

### Gaps
- I did not find a quantified rank correlation between early-stopped and final RL runs; the Hyperband/ASHA papers themselves and the Wu et al. numbers on RL were not read. Draws on a snippet-level source (2402.13641) for the low-fidelity caveat.
- Claims about Hyperband's resource-allocation guarantees are from my memory and not cited here.

Loop change 3: add a plan.json "long-fidelity check" job: take the 2-3 best candidates (by pooled mean over all seeds so far, not by best single seed) and run each at 3x the budget (15 min) with 3 seeds against a baseline at the same budget. Cost ~9 runs x 15 min = 135 GPU-min for 3 candidates (or 45 min for one candidate x 3 seeds vs baseline x 3). Tests whether the short-horizon proxy ranks correctly at all. Respects rules. If 15-min baselines vs candidates correlate with the 5-min results, the 5-min screen is trusted; if not, the 5-min loop is not measuring the right thing.

## 4. How many seeds, and variance reduction (CRN, control variates, games vs seeds)

### Takeaway
At sd ~0.0115 per run, resolving +0.015 with 80% power needs about 6 runs per arm and +0.01 needs about 13-14 per arm, unless the variance is cut. Cheapest variance cuts: fixed-step instead of wall-clock budget, a concurrently run baseline pool, shared eval deals, and more eval games only if eval-sampling is the dominant term.

### Cited Findings
- Power in RL comparisons is computed from the Welch t-distribution for a given N and effect size; there is no closed-form shortcut; N=5 had 51% miss rate in their example — [Colas et al. 2018](https://ar5iv.labs.arxiv.org/html/1806.08295)
- Fishtest-style pairing reduces required games ~17-20% in the pentanomial example — [vdbergh/pentanomial](https://github.com/vdbergh/pentanomial)
- Henderson et al. use a fixed set of seeds across all compared runs — [Henderson et al. 2018](https://ar5iv.labs.arxiv.org/html/1709.06560)

### Inferences (all my calculations, one-sided alpha .05, power .8, so z = 1.645 + 0.84 = 2.49)
- Required runs per arm k = 2*(2.49*sd/effect)^2.
  - sd 0.0115, effect 0.015: k = 5.9, so 6 per arm (12 runs, 60 min; 6 candidate runs if the baseline pool is shared).
  - sd 0.0115, effect 0.010: k = 13.2, so 14 per arm (140 min).
  - sd 0.0115, effect 0.020: k = 3.3, so 4 per arm.
  - sd 0.0075 (if CRN/fixed-step removes training variance, only eval sampling left), effect 0.01: k = 5.5, so 6 per arm.
- Shared baseline pool: run 6-8 baseline seeds once (30-40 min), reuse for every candidate within a run of experiments; each candidate then costs k runs, not 2k. Baselines must be interleaved over the day, not run once, in case hardware state drifts (thermal, background load); the 80% GPU cap and other jobs make this a real risk.
- Control variate: subtracting the same-seed baseline only helps if same-seed runs are positively correlated. With changed code the RNG streams diverge quickly, so correlation is probably low; test it with the 6-seed baseline pool vs one candidate (cost nothing extra). If the correlation is ~0.3, variance of the difference drops ~30%.
- Games vs seeds: if the split in section 1 shows eval var 5.6e-5 of total 1.3e-4, doubling eval games lowers sd from 0.0115 to ~0.0098 (15%); quadrupling gives ~0.0089. Training-seed replication cuts both terms. Prefer eval games only up to the point eval var ≈ training var, since extra eval is ~3 GPU-min per 4,500 games (estimated; check from the eval log).
- Antithetic seeds: no source found; do not recommend.

### Gaps
- Per-component timing (eval vs train) in fixed.py was not inspected; the 3-GPU-min figure is a guess.
- Jordan et al. 2020 (percentile/uncertainty-based evaluation) was only seen via search results; seed-count details not verified.

Loop change 4: add a "baseline pool" job to plan.json: 6 baseline seeds at the start of each session and 2 per day thereafter, M stored with seed and time. Keep decision becomes: candidate mean over k=3 seeds minus the pool mean (Welch t-test one-sided, p < 0.05, with k extended to 6 if p is between 0.05 and 0.3). Cost 30 GPU-min up front; each candidate 15-30 min. Respects rules. Under sd 0.0115 this reliably detects ~+0.02 at k=4, and +0.015 at k=6.

## 5. Experience with Karpathy-style autoresearch on noisy metrics

### Takeaway
The public descriptions I found use a plain "improve then keep, else revert" rule with a fixed time budget and mention no noise handling; one write-up reports 8 kept out of 47 experiments with a 2.9% gain. I found no published treatment of the noise-floor problem in these loops beyond a single aerospace-agent paper that measures seed noise first.

### Cited Findings
- Setup: fixed prepare.py, agent-edited train.py, human-written program.md; metric val_bpb with a fixed time budget; keep if val_bpb improves, otherwise git reset — [Verdent guide](https://verdent.ai/guides/what-is-autoresearch-karpathy), [Menon Lab](https://themenonlab.blog/blog/karpathy-autoresearch-autonomous-ml-experiments)
- An overnight run reported 47 experiments, 8 kept, val_bpb 1.847 to 1.793; the write-up says nothing about seeds or whether small gains exceeded noise — [HackerNoon](https://hackernoon.com/i-let-karpathys-autoresearch-agent-run-overnight)
- An LLM research agent for aerospace control proposes measuring seed noise on a fixed baseline first and crediting gains in units of that sd — [arXiv 2606.20394](https://arxiv.org/pdf/2606.20394) (snippet only)

### Inferences
- Karpathy's val_bpb is much less noisy than a self-play share (a language-model loss on a fixed validation set), so "keep if lower" works there; the same rule on M with sd ~ delta produces false keeps of about 1 in 6 at seed 1, which is what the audit saw.
- ar/ already departs from the baseline rule by adding a delta and a confirm; the problem is that both thresholds were set from an underestimated sd.

### Gaps
- I did not find the Karpathy repo's own README/discussions in the search results, so whether the maintainers discuss noise is unknown. No published rank-correlation of 5-minute proxies in such loops was found.

Loop change 5: stop the agent from using single-seed gaps as the basis of the next idea. Add to program.md (and have fixed.py print) "noise sd (pooled) = 0.0115; a gap under 2 sd (0.023) at one seed is not a trend", and make fixed.py log the running pooled sd after each confirm. Cost 0 GPU. Edits program.md/fixed.py only (the audit is not allowed to touch them; this is for the owner). Respects all rules.

## Suggested order (cheapest first, total ~2-3 GPU-hours)
1. Loop change 1 (~15 min): determinism and eval/train variance split; reset the sd to the pooled estimate.
2. Loop change 4 baseline pool (~30 min), reusing the same pool for a first multi-seed test of the best 2 candidates so far (LAM 0.8, frozen anchor, curriculum: 3 candidates x 3 more seeds = 45 min).
3. Loop change 2 (paired sequential confirm) in fixed.py once the pool exists.
4. Loop change 3 (15-min check) only if step 2 shows a candidate with mean gain >= +0.01.
Biggest uncertainty: the sd of 0.0115 rests on 3 pairs (3 df); step 1 and the pool will replace it with a 10+ df estimate.
