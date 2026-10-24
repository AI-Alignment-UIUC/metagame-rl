# Co-optimising a design and its controller (bilevel / two-timescale learning) as an analogue of decks and pilot

Mapping used throughout: deck = design/morphology/level; pilot = controller; draft head = design optimiser; population turnover = random-immigrant injection; "deck type" = morphology niche. The metagame-rl pilot is one shared ("universal") controller that keeps its knowledge across generations, which makes it Lamarckian. In the robot literature that is the setting most exposed to the "first-mover" bias described below. Failure-mode tags [F1]-[F6] refer to the list in the assignment.

## Q1. Morphology-control co-design: what causes premature convergence, and do protection of new designs, universal/shared controllers or controller fine-tuning fix it?

### Takeaway
Across 10 years of work from one lab (Cheney, then Mertan and Cheney) and several independent groups, the cause is consistent. A controller adapted to the incumbent design makes every new design look worse than it really is at the moment it is judged. Selection then discards it, so the design search converges early while the controller keeps improving. Protecting new designs (age-Pareto "morphological innovation protection"), using controllers that transfer to new bodies, adding a short fine-tune before judging, and budgeting adaptive learning each help in some studies. None of them is a full fix. One near-exhaustive 2025-26 study found that protection alone did not remove the undervaluation.

### Cited Findings
- **Sims (1994) baseline stagnation.** Sims-style evolved creatures averaged 6.042 segments. Two decades of later work did not visibly exceed that complexity despite far more compute. — [Cheney et al. 2018, J. R. Soc. Interface 15:20170937](https://meclab.w3.uvm.edu/papers/2018_RoySoc_Cheney.pdf)
- **Cheney, Bongard, SunSpiral, Lipson (ALIFE XV, 2016), "On the difficulty of co-optimizing morphology and control".** Method: freeze the morphology at generation g, then optimise control only. Freezing at any g ≥ 25 (of 5000) gave no significant fitness difference from full co-optimisation (p ≥ 0.0604). Freezing the controller instead mattered until 100-250 generations. The best-of-run morphology appeared on average at generation 558, versus generation 2926 for the best controller (p < 0.001). Their interpretation is that a body mutation "scrambles" the controller's interface to the world, so the design search stalls first. [F1, F5] — [Cheney et al. 2016 PDF](https://meclab.w3.uvm.edu/papers/2016_ALife_Cheney.pdf)
- **Cheney et al. (J. R. Soc. Interface, 2018), the embodied-cognition hypothesis.** "most evolutionary changes to morphology tend to adversely impact sensorimotor control." Specialisation of brain and body to each other "creates local optima in the search space and premature convergence to suboptimal designs." Traditional EAs reject body mutations that are immediately worse, "as the initially poor fitness may be due to the robot controller's specialization for producing behaviour in the old morphology." — [Cheney et al. 2018](https://meclab.w3.uvm.edu/papers/2018_RoySoc_Cheney.pdf); [arXiv 1706.06133](https://arxiv.org/abs/1706.06133)
- **How morphological innovation protection (MIP) works.** The algorithm tracks each individual's "morphological age" (generations since its last body mutation) and selects on the Pareto front of age × fitness. A robot is removed only if another robot is fitter and has had less controller readaptation. The method needs no fixed readaptation window. It "allows fitness comparisons between all new child morphologies that have had equal readaptation time." It is inspired by Age-Fitness Pareto Optimisation (Schmidt & Lipson) and ALPS (Hornby 2006). [F1, F3] — [Cheney et al. 2018](https://meclab.w3.uvm.edu/papers/2018_RoySoc_Cheney.pdf)
- **MIP results (30 runs each, (μ,λ)-ES with 25+25, 5000 generations).**
  - No protection: 21.717 voxels travelled. MIP: 31.953 (p = 6.067e-6).
  - A control that protects *controller* innovations instead (same extra diversity and multi-objective search) gave 22.049, not better than no protection (p = 0.240). The gain is therefore not generic diversity.
  - Without protection, fitness barely moved from generation 1000 to 5000 (20.988 to 21.717, p = 0.085). MIP kept improving (25.925 to 31.953, p = 0.013).
  - Unique best-so-far morphologies per run: 24.179 with MIP vs 10.115 without (p = 1.555e-6). "Overtakes" (a child body that starts worse, later beats its parent after controller readaptation): 76.714 vs 1.432 per run.
  - Changing the ratio of body to controller mutations (1:99 to 99:1) had no significant effect on premature convergence without protection.
  - [F1, F3] — [Cheney et al. 2018](https://meclab.w3.uvm.edu/papers/2018_RoySoc_Cheney.pdf)
- **MIP at higher resolution (10×10×10 voxels).** Resetting morphological age only after a "gross" change (more than 20% of voxels altered; chosen by a sweep over 0-50%) gave 60.728 voxels. No protection gave 32.575 (p = 1.208e-4), controller protection 35.375, and MIP with no threshold 43.340 (p = 0.063 vs thresholded). With closed-loop neural controllers, thresholded MIP gave 31.313 versus 13.941, 15.356 and 17.224 for the other treatments (all p ≤ 7.287e-8). — [Cheney et al. 2018](https://meclab.w3.uvm.edu/papers/2018_RoySoc_Cheney.pdf)
- **Mertan & Cheney (EuroGP 2024).** Body-only optimisation with a *fixed, zero-parameter* controller beat brain-body co-optimisation in all 4 settings (2 environments × 2 morphology sizes; all p < 0.005), and converged faster.
  - Training a learnable controller from scratch on the fixed-controller champion bodies beat the co-optimised learnable champions in 3 of 4 settings (p < 0.05). Good bodies existed that co-optimisation never found.
  - Re-training a controller from scratch on the co-optimised champions' own bodies gave indistinguishable results (all p > 0.44). Their controllers had already converged, so "the struggle... is due to sub-par morphologies more so than sub-par controllers."
  - [F1, F2] — [Mertan & Cheney 2024, arXiv 2402.09231](https://arxiv.org/abs/2402.09231)
- **Mertan & Cheney 2024, "body-centric" view.** Each body has a *range* of fitness values that depends on how trained its controller is. "Body plans that we found early in the co-optimization process accrue more controller optimization steps, climbing up to their maximum fitness value – an example of a first-mover advantage." Later bodies "can't compete with first-movers until a controller is optimized for them... but typically can't survive long enough to accrue control optimization." Proposed remedy families:
  1. give new bodies more evaluation resources;
  2. reduce the drop in fitness at birth, via coordinated-change encodings or controllers robust to body changes.

  The authors explicitly draw the analogy to weight-sharing supernets in neural architecture search (NAS), to surrogate fitness models and to bandits. — [Mertan & Cheney 2024](https://arxiv.org/abs/2402.09231)
- **Mertan & Cheney (GECCO 2023), modular controllers.** Decentralised controllers (one shared small net per voxel, reading a local 3×3 patch) lost less fitness after body mutations than global controllers. They reached higher champion fitness: 10.42 vs 9.67 over 100 runs (p = 0.0016). They also converged faster: 80% of final fitness at generation 439.84 vs 709.61, 99% at 2710.06 vs 3059.37 (all p < 0.05).
  - Transfer to mutated neighbour bodies dropped with mutation distance for both controller types.
  - Both recovered with "as little as one generation of controller finetuning" ("one-shot transfer").
  - Modular controllers were "never worse and oftentimes better" at transfer, yet no better on a single fixed body. The benefit is robustness to design change, not raw skill. [F2, F3] — [Mertan & Cheney 2023 (NSF PAR copy)](https://par.nsf.gov/servlets/purl/10458459)
- **Mertan & Cheney (Artificial Life journal, accepted; extended ALIFE 2025 paper), near-exhaustive ground truth.** They trained a controller for every one of 1,305,840 voxel robots.
  - Out of 100 runs each, a near-optimal body (top-30% fitness band, 308 morphologies) was found 17 times by AFPO, 22 by MAP-Elites and 13 by MIP.
  - Morphology-only AFPO given true fitness "consistently found near-optimal morphologies" with fewer resources.
  - Search "at times, gets stuck on morphologies one mutation away from better ones." Run champions that were not even local maxima: AFPO 78/100, MAP-Elites 38, MIP 57.
  - Fitness drops after body mutations were significantly larger than the true fitness differences. All three algorithms repeatedly eliminated offspring that selection on true fitness would have kept.
  - Their MIP variant (every new body protected, no threshold) "did not fix undervaluation" and was slightly worse on average, although it produced the single best champion.
  - Rankings among top morphologies had not stabilised after 300 generations of controller optimisation. Early selection among good bodies was therefore near-uninformed. [F1, F3] — [Mertan & Cheney, arXiv 2508.17464](https://arxiv.org/abs/2508.17464)
- **Same study, goal-switching benefit.** Co-optimisation also produced body-controller pairs that optimising the controller alone on a fixed body could not match (probability < 0.01 for 2 of 5 top bodies). Fully decoupling the levels (train each design's controller to convergence) is therefore not free: it loses this benefit. The authors list the following remedies:
  - decoupled bi-level optimisation;
  - adaptive or lifetime learning and Lamarckian inheritance;
  - transferable or multi-morphology controllers;
  - generative or differentiable design.

  — [Mertan & Cheney, arXiv 2508.17464](https://arxiv.org/abs/2508.17464)
- **Mertan & Cheney (GECCO 2025), "Pollination" in MAP-Elites.** Every 500 generations, a single controller is distilled by supervised imitation from a random archive solution and its 4 Moore neighbours (niches). It replaces the teachers' controllers only where it performs comparably.
  - Body-mutation success, cross-niche migrations, total and maximum quality-diversity (QD) quality, and run champions all improved.
  - Trade-off: pollinated controllers were more fragile to *controller* mutations.
  - The authors call it a proof of concept, and the text gives few exact numbers. [F1, F2] — [Mertan & Cheney 2025, arXiv 2504.06523](https://arxiv.org/abs/2504.06523)
- **Song et al. (arXiv, 24 Aug 2026, preprint), "AdaControl".** Evaluating fitness before the controller has finished learning "underestimates true potential and favors fast learners." That bias narrows design exploration and reduces morphological diversity. They argue the "morphological Baldwin effect" is an artifact of this bias. AdaControl detects when selection is favouring learning speed and only then allocates the minimum control learning needed for unbiased evaluation. Reported result: a simple GA rivals generative co-design methods with up to 80% less compute than exhaustive control learning. Not peer-reviewed. [F1, F3] — [Song et al. 2026, arXiv 2608.23100](https://arxiv.org/abs/2608.23100)
- **Gupta, Savarese, Ganguli, Fei-Fei (Nature Communications 2021), DERL.**
  - Setup: 576 agents; asynchronous tournaments of 4. The *oldest* member is removed, not the least fit. Each child's controller is trained *from scratch* with PPO for 5M steps, so inheritance is Darwinian, not Lamarckian. About 4,000 morphologies over about 10 generations, on 1,152 CPUs in under 16 h.
  - Results: about 15-20 lineages survive per run. Small asynchronous tournaments let low-fitness founders still produce top descendants, which "maintains diversity." Average learning time of the top 100 agents is "cut in half" within 10 generations (the Baldwin effect).
  - [F1] — [Gupta et al. 2021, arXiv 2102.02202](https://arxiv.org/html/2102.02202v1)
- **Schaff, Yunis, Chakrabarti, Walter (arXiv 1801.01432; ICRA 2019 per my background knowledge, not verified here).** One controller conditioned on the design parameters, trained over a *distribution* of designs.
  - The distribution is a mixture of Gaussians that starts at high entropy. Mixing is uniform, and the lowest-reward components are eliminated, halving the number every N iterations. A warm-up updates only the policy before designs move.
  - Failure case: on Ant-on-incline, 7 of 8 seeds stuck at a local optimum in which the controller "chooses the 'safer' option of having all samples stand still." The design distribution then moved "towards large designs that balance using little energy, making locomotion even harder."
  - They fixed it by halving the reward for staying upright. That is reward shaping, which is disallowed here. [F1, F5] — [Schaff et al., arXiv 1801.01432](https://arxiv.org/abs/1801.01432)
- **Bhatia et al. (NeurIPS 2021), Evolution Gym.** Bi-level loop: optimise a controller with PPO for each proposed design, then update designs (GA, Bayesian optimisation or CPPN-NEAT). A simple GA with elitism (keep the top x%, x decayed from 60 to 0) outperformed the other two overall. "All tested algorithms fail to find robots that succeed in our hardest environments." — [Bhatia et al., arXiv 2201.09863](https://arxiv.org/abs/2201.09863)

### Inferences
- **[F1] The walls are the incumbent "first movers".** The shared pilot has spent most of its updates on wall-vs-wall and wall-vs-mutant games, so it plays walls near their ceiling. A Trainer-heavy candidate (Rain Dance, Haymaker) is scored at the low end of its own fitness range. That reproduces the relapse within 10-15 iterations seen after any perturbation. It is the same signature as Cheney 2018's no-protection runs: gross design changes absent after about 1% of the run, and few unique best-so-far designs.
- **[F1, F5] A possible "fast learner" reason that walls and Energy-heavy piles win.** This is my inference, not a finding. Decks whose value needs little decision skill (attach Energy, heal, stall, win by deck-out) look good under an immature or non-specialised pilot. Trainer-heavy decks need precise sequencing to show their value. The AdaControl result (premature evaluation favours fast learners) and Schaff's "safer option" collapse both predict this. A test: does the wall's win rate saturate after fewer pilot updates on a new pilot than the human lists' does?
- **[F1, F3] Diversity alone is not the lever.** Cheney 2018's controller-protection control shows generic diversity is not what helps. The thing to protect is a new deck *from comparison against decks whose pilot experience is larger*. Type caps and frequent turnover (already tried) add diversity but do not equalise pilot-adaptation age. That may be why they kept the pilot general without changing the decks.
- **[F2] F2 is a direct measurement of the "fitness range per design" in Mertan 2024.** The walls score 0.72-0.76 with their co-adapted pilot but 0.23-0.24 with a generalist. Mertan's "re-train on the champion's body" check suggests a matching diagnostic, for evaluation only: fine-tune copies of the pilot equally on (a) a wall and (b) a human list, then replay the match.
- **[F1] The absence of an Energy-light archetype in the population is weak evidence.** Mertan & Cheney 2026 shows that even with protection, co-optimisation finds near-optimal designs only 13-22% of the time in a small, fully mapped space.

### Gaps
- No co-design paper studied *competitive* (adversarial) evaluation, in which a design's fitness depends on the other designs in the population. All results above are single-agent fitness. How the first-mover advantage interacts with intransitive matchups is untested.
- Exact numbers for Pollination (migration counts, QD scores, p-values) were not in the text I could access.
- Sims 1994 reports no quantitative premature-convergence analysis that I could find. Its stagnation is documented only indirectly via Cheney 2018.
- I could not confirm the internal details of AdaControl (the bias detector, budget rule), only its abstract.

## Q2. Shared (universal) controllers vs per-design controllers for evaluating designs fairly; "embodied" bias toward designs the current controller already handles

### Takeaway
Shared controllers are the only affordable option, but they rank designs badly. In NAS, where the same issue is studied at scale, weight-sharing rankings are near-uncorrelated with stand-alone rankings. The bias is towards candidates that received more training or that work without well-trained weights. Documented fixes are:
- equal training opportunity per candidate ("strict fairness");
- several partial shared models, one per region of the design space;
- a population network plus per-design fine-tuned copies;
- performance-balanced sampling in multi-design training.

### Cited Findings
- **Wang, Zhou, Fidler, Ba (ICLR 2019), Neural Graph Evolution (NGE).** Graph-neural-network (GNN) controllers let a mutated design inherit its parent's parameters ("amortized fitness"), so the child's fitness is measured with an inherited, not converged, controller. Graph Mutation with Uncertainty (GM-UC) balances exploration and exploitation. "Orders of magnitude more efficient" than prior search; it finds designs within a day on one 64-core machine. — [Wang et al., arXiv 1906.05370](https://arxiv.org/abs/1906.05370)
- **Yuan, Song, Luo, Sun, Kitani (ICLR 2022 oral), Transform2Act.** One transform-and-control policy (a GNN plus joint-specialised MLPs, JSMLPs) designs the body inside each episode, then controls it, with experience shared across designs.
  - Evolutionary methods like NGE try only N = 16-100 designs per epoch. Transform2Act's effective number of designs tried can exceed 2000.
  - Ablation: without JSMLPs, "designs... are overly symmetric with little per-joint specialization, which leads to worse performance." A fully shared policy pulled designs toward homogeneity. — [Yuan et al., arXiv 2110.03659](https://arxiv.org/abs/2110.03659)
- **Luck, Ben Amor, Calandra (arXiv 1911.06832; CoRL 2019 per my background knowledge, not verified here).** The learned Q-function evaluates designs, $\max_\xi \mathbb{E}[Q(s, \pi(s,\xi), \xi)]$, in place of rollouts.
  - Two network sets: a *population* actor-critic trained on all designs, and *individual* networks initialised from it and trained mostly on the current design. 10% of each individual batch comes from the population buffer. Individual networks get 1000 updates per episode vs 250 for the population networks.
  - Design choice alternates between exploitation (argmax under Q) and exploration. Random exploration beat novelty search.
  - [F2, F3] — [Luck et al., arXiv 1911.06832](https://arxiv.org/abs/1911.06832)
- **Gupta, Fan, Ganguli, Fei-Fei (ICLR 2022), MetaMorph.** A transformer universal controller over a modular design space, conditioned on morphology tokens. It shows zero-shot generalisation to unseen morphologies and sample-efficient transfer.
  - Because "some morphologies might be inherently better suited for the pre-training task," they use *dynamic replay buffer balancing*: robot k is sampled with probability ∝ E_k^β, a smoothed performance metric, so poorly-performing morphologies get more experience.
  - Without balancing, on average 10-15% of robots fail to learn a good policy. [F2, F4] — [Gupta et al., arXiv 2203.11931](https://arxiv.org/abs/2203.11931)
- **Yu, Sciuto, Jaggi, Musat, Salzmann (ICLR 2020), "Evaluating the search phase of NAS".** Architecture rankings with vs without weight sharing are "entirely uncorrelated" in an RNN space (Kendall τ = −0.004 over 10 runs) and weakly correlated in a CNN space (τ = 0.195). State-of-the-art NAS "perform[s] similarly to the random policy." [F3] — [Yu et al., arXiv 1902.08142](https://arxiv.org/abs/1902.08142)
- **Chu, Zhang, Xu (arXiv 1907.01845; ICCV 2021 per my background knowledge), FairNAS.**
  - Diagnosis: in weight-sharing NAS, candidates "who have better initial performance are more likely to be sampled or to maintain higher coefficients", which introduces "gradually increasing biases." DARTS cells end up with "an excessive number of skip connections."
  - Fix: "strict fairness", i.e. equal optimisation opportunities for every choice block at every step. It reaches Kendall τ = 0.7412 on NAS-Bench-201, versus an average τ of 0.474 for an earlier costly method.
  - [F1, F2] — [Chu et al., arXiv 1907.01845](https://arxiv.org/abs/1907.01845)
- **Zhao, Wang, Tian, Fonseca, Guo (ICML 2021), few-shot NAS.** One supernet mis-predicts because of "co-adaption among operations." Splitting the space into up to 7 *sub-supernets*, each covering one region, "improves the accuracy of architecture evaluation with a small increase of evaluation cost." This is a direct analogue of per-niche pilots. [F2] — [Zhao et al., arXiv 2006.06863](https://arxiv.org/abs/2006.06863)
- **Zela et al. (ICLR 2020), "Understanding and robustifying DARTS".** Bilevel DARTS collapses to parameter-less skip connections, and even picks a deliberately harmful "Noise" op for 5 of 8 operations in one space.
  - The dominant Hessian eigenvalue of validation loss with respect to the architecture parameters correlates with generalisation error.
  - Early stopping on that signal, or stronger regularisation of the *inner* problem, makes the search robust.
  - [F1] — [Zela et al., arXiv 1909.09656](https://arxiv.org/abs/1909.09656)
- **Mertan & Cheney 2024 on the same point.** They explicitly compare robot co-design to "supernet weight-sharing algorithms in the Neural Architecture Search literature." They call for meta-learning, transfer and few-shot methods to share "fitness approximators across disparate body plans." — [Mertan & Cheney 2024](https://arxiv.org/abs/2402.09231)
- **Mertan & Cheney 2023 on joint training.** Joint training of one controller on 4 fixed bodies (fitness = the *minimum* over bodies) reached comparable performance for modular and global controllers, but performance on multiple bodies was lower than on single bodies. "Performance and generalization are competing objectives." — [Mertan & Cheney 2023](https://par.nsf.gov/servlets/purl/10458459)
- **DERL (from-scratch controller per child).** It keeps about 15-20 lineages but is costly: 5M steps per morphology and 1,152 CPUs. It shows a strong Baldwin effect: selection favoured morphologies that learn fast. — [Gupta et al. 2021](https://arxiv.org/html/2102.02202v1)

### Inferences
- **[F2] F2 matches the weight-sharing NAS bias in kind.**
  - The pilot is a supernet over decks, and population games are the "sampling" that trains it.
  - Deck types that dominate the population get more pilot updates (FairNAS's "Matthew effect" in all but name), so they are evaluated more favourably and keep dominating.
  - The draft head's REINFORCE signal comes from this biased evaluator. Yu et al.'s τ ≈ 0-0.2 suggests the 73%-of-decks-moved-at-noise-floor result is expected, not anomalous.
- **[F1] A DARTS-like reading of "Energy over Trainers".** This is my inference. Basic Energy is the deck-building analogue of a parameter-free skip connection: its value barely depends on pilot skill. Trainers are like parametric operations: their value depends on how well the shared pilot has learnt to use them. Weight-sharing evaluators systematically over-select the former. Zela's remedies are early stopping on a sharpness signal and stronger inner regularisation. For decks that suggests capping how fast deck composition can move while the pilot's loss surface for the current decks is still sharp or unstable.
- **[F2, F4] Concrete fairness changes.**
  1. Sample pilot-training games so that each deck *type* (cluster), not each deck, gets equal updates (FairNAS strict fairness). Better: weight towards types where the pilot underperforms, as in MetaMorph's E_k^β balancing.
  2. Maintain K pilot adapters or heads, one per archetype cluster (few-shot NAS sub-supernets; Luck's individual networks), on top of the shared encoder. Judge a deck by the better of the generalist and its niche head.
  3. Periodically distil the niche heads back into the generalist (Pollination).
- **[F3] Fast first-pass ranking.** Luck's Q-as-surrogate suggests the pilot's value head could pre-rank candidate edits cheaply. Given the evaluator bias, it should only shortlist candidates, not make the decision.

### Gaps
- No study I found measures how biased a *Lamarckian, continuously trained* universal controller is compared with one trained from scratch per design in the *same* co-design run. Mertan & Cheney 2026's ground-truth map is the closest.
- MetaMorph does not co-design. It trains on a fixed set of morphologies, so its balancing result is about controller quality, not design selection.

## Q3. Environment/level design with co-learning agents (POET, Enhanced POET, PAIRED, PLR⊥, ACCEL): how they keep a population of challenges and agents productive; transfer between pairs

### Takeaway
Open-ended co-design systems stay productive through three mechanisms:
1. **Admission criterion:** new designs are admitted only if they are neither too easy nor too hard for current agents. POET used a hand-set reward band. PAIRED, PLR⊥ and ACCEL use regret.
2. **Paired agents with goal-switching:** each design keeps its own agent, and agents are transferred between designs only if they beat the incumbent after a fine-tuning step, under a stricter threshold to block noisy false positives.
3. **Curated training:** the shared agent trains only on curated high-regret designs.

All three map naturally onto the deck/pilot loop.

### Cited Findings
- **Wang, Lehman, Clune, Stanley (arXiv 2019), POET.**
  - Environment-agent *pairs*. Each agent is optimised (by evolution strategies, ES) in its own environment.
  - Children of environments are admitted only if they meet a minimal criterion, 50 ≤ E_child(θ_child) ≤ 300, i.e. "not too hard and not too easy for the current population."
  - Every N_transfer iterations, every other agent is tried in each environment and replaces the incumbent if better ("goal switching").
  - Results:
    - Environments solved by POET could not be solved by direct ES from scratch, nor by a direct-path curriculum.
    - With transfers disabled ("POET without transfer"), coverage fell, and "no extremely challenging environments are solved at all."
  - [F1, F2] — [Wang et al., arXiv 1901.01753](https://arxiv.org/abs/1901.01753)
- **Wang et al. (Enhanced POET, arXiv 2003.08536; ICML 2020 per my background knowledge).**
  - Transfer in original POET was "prone to 'false positives' due to stochasticity in RL optimization and a low bar for replacing more proven incumbents."
  - Fix: a candidate must beat "the maximum of the 5 most recent scores of the incumbent" on *both* direct and fine-tuning transfer. This matched original POET's results with 79.7 ± 1.67% of the computation.
  - PATA-EC: a domain-general environment novelty measure. Environments are characterised by the (clipped, normalised) *ranking* of all agents' scores in them, i.e. "how agents behave in it." It matched the hand-designed metric's diversity at 82.4 ± 7.31% extra computation.
  - Environments are archived (still used for novelty) when the population cap is reached.
  - Neither direct optimisation nor hand-made curricula solved middle and late-stage POET environments (p < 0.01).
  - [F1, F3] — [Wang et al., arXiv 2003.08536](https://arxiv.org/abs/2003.08536)
- **Dennis, Jaques et al. (NeurIPS 2020), PAIRED.** Domain randomisation "cannot generate structure or adapt the difficulty," and a minimax adversary "leads to worst-case environments that are often unsolvable." PAIRED's adversary maximises *regret*, the antagonist agent's return minus the protagonist's. This yields solvable but hard environments and better zero-shot transfer. — [Dennis et al., arXiv 2012.02096](https://arxiv.org/abs/2012.02096)
- **Jiang, Dennis et al. (NeurIPS 2021), Replay-guided UED / PLR⊥.**
  - "By stopping the agent from updating its policy on uncurated levels (training on less data), we can improve the convergence to Nash equilibria." Random levels are rolled out under a stop-gradient only to *score* them. The policy trains only on replayed high-regret levels.
  - PLR⊥ provably follows a minimax-regret strategy at Nash equilibrium.
  - Failure mode: "PAIRED often overexploits the difference in the students, leading to simple tracks that incidentally favor the antagonist." [F2, F3, F4] — [Jiang et al., arXiv 2110.02439](https://arxiv.org/abs/2110.02439)
- **Parker-Holder, Jiang et al. (arXiv 2203.01302; ICML 2022 per my background knowledge), ACCEL.**
  - Regret-based level evolution: "small edits (e.g. mutations) to previously high-regret levels." "The student only trains on replay levels."
  - "Regret serves as a domain-agnostic fitness for evolution", replacing POET's hand-tuned [50, 300] filter.
  - Curricula "start simple but become increasingly complex." [F1, F3] — [Parker-Holder et al., arXiv 2203.01302](https://arxiv.org/abs/2203.01302)

### Inferences
- **[F2, F4] Deck regret as the curation signal.** Define it as regret(d) = win rate of deck d under a *pilot fine-tuned on d* minus its win rate under the shared pilot. This equals Mertan's "range of fitness per body" and the PAIRED antagonist/protagonist gap.
  - High-regret decks are exactly those the shared pilot under-plays. Training the shared pilot *only* on a curated buffer of high-regret decks (PLR⊥) pushes it to become general instead of wall-specialised.
  - This needs no human data and carries to any card game.
  - A cheaper proxy is the positive value loss or advantage magnitude PLR uses, computed from the pilot's own critic on games with that deck.
- **[F1, F3] ACCEL-style draft head.** A draft head that makes small edits to high-regret decks is a direct translation of ACCEL. It replaces "edit towards higher win rate under the current pilot", which is the first-mover-biased objective.
- **[F3] Exploiter drift.** The exploiter heads that drifted to the main type were judged only against the main head's decks under the shared pilot. In PAIRED terms they had no antagonist baseline, so their objective rewarded whatever the shared pilot plays best. Adding a regret term, or the PATA-EC-style novelty gate below, would penalise that.
- **[F1] Matchup-profile novelty gate.** PATA-EC transfers directly: characterise each deck by the rank order of a fixed panel of opponent decks' win rates against it, and admit decks only if novel by that profile. This is game-general and needs no hand-coded archetype features.
- **[F3] Stricter acceptance threshold.** Enhanced POET's rule (beat the max of the incumbent's last 5 scores, on both direct and fine-tuned evaluation) is a cheap fix for the noise-floor moves. Combined with a fine-tune step, it also stops rejecting good-but-unadapted decks.

### Gaps
- POET, PAIRED and ACCEL design *environments for one agent*. None has designs that compete against each other (deck vs deck), so intransitivity and metagame cycling are outside their theory.
- PLR⊥'s robustness guarantee assumes the student can reach a Nash equilibrium of the regret game. It is unclear whether that holds with a 53-turn, partially observed card game.
- No paper here addresses long-horizon tactical weakness [F4] or turn-limit draws [F6] directly.

## Q4. Bilevel optimisation and two-timescale stability results (learning-rate ratios, inner-loop fine-tuning before outer evaluation) bearing on F2-F3

### Takeaway
Theory for leader-follower (Stackelberg) and bilevel learning requires the inner player, here the pilot, to move on a *faster* timescale than the outer player, here the decks. The outer step should use the inner player's *reaction*, not its current state. Unrolled GANs implement that by letting the inner player take a few steps before the outer update. In the deck loop, decks move every iteration (73% moved even at noise) while the pilot is judged as-is, which breaks both conditions.

### Cited Findings
- **Fiez, Chasnov, Ratliff (arXiv 1906.01217; ICML 2020 per my background knowledge).** In hierarchical learning, "the leader is assumed to be learning at a slower rate than the follower so that γ1,k = o(γ2,k)." The leader's gradient includes the implicit term through the follower's reaction curve:
  $Df_1 = D_1 f_1 - D_2 f_1 (D_2^2 f_2)^{-1} D_{21} f_2$.
  Unrolled GANs, where the discriminator does a finite inner roll-out before each generator update, have "the same effect as a deterministic timescale separation." — [Fiez et al., arXiv 1906.01217](https://arxiv.org/abs/1906.01217)
- **Hong, Wai, Wang, Yang (arXiv 2007.05170; SIAM J. Optim. per my background knowledge), two-timescale stochastic approximation (TTSA) for bilevel problems.**
  - A larger step size for the inner problem and a smaller one for the outer problem. For example, with a strongly convex outer objective, α_k = O(k^−1) and β_k = O(k^−2/3), giving O(K^−2/3) error.
  - Under weak convexity it reaches O(K^−2/5)-stationarity. Natural actor-critic is shown to be a special case.
  - Assumes a strongly convex inner problem, which is far from PPO on a card game. — [Hong et al., arXiv 2007.05170](https://arxiv.org/abs/2007.05170)
- **Cheney et al. 2018 (biological framing).** "If gross morphological changes tend to occur more slowly than the rate of learning in the brain... the bias seen in these robotic results towards greater success when controllers rapidly readapt to more gradual morphological changes... may be consistent." — [Cheney et al. 2018](https://meclab.w3.uvm.edu/papers/2018_RoySoc_Cheney.pdf)
- **Fine-tune before judging, empirically.**
  - POET and Enhanced POET's "fine-tuning transfer" takes one optimisation step before comparison ([Enhanced POET](https://arxiv.org/abs/2003.08536)).
  - Mertan & Cheney 2023: one generation of controller fine-tuning recovers most transfer loss ([GECCO 2023](https://par.nsf.gov/servlets/purl/10458459)).
  - Luck et al.: individual networks get 4× the updates of the population networks to "adapt quickly" ([arXiv 1911.06832](https://arxiv.org/abs/1911.06832)).
  - AdaControl: allocates just enough inner learning when bias is detected ([arXiv 2608.23100](https://arxiv.org/abs/2608.23100)).
- **Zela et al.: inner regularisation and early stopping stabilise bilevel search.** Stronger regularisation of the *inner* objective, or stopping when the dominant Hessian eigenvalue with respect to the architecture parameters rises, avoids the skip-connection collapse. — [Zela et al., arXiv 1909.09656](https://arxiv.org/abs/1909.09656)
- **Mertan & Cheney 2026: full decoupling is not free either.** Fully decoupled bi-level optimisation loses the goal-switching benefit. Co-optimisation found pairs that controller-only optimisation on the final body could not match. — [arXiv 2508.17464](https://arxiv.org/abs/2508.17464)

### Inferences
- **[F2, F3] Make decks the slow player.** For example:
  - a deck may move at most once per M pilot updates;
  - an *archetype-level* change may happen only after its candidate has been fine-tuned on for k pilot steps;
  - the deck-acceptance test should compare "candidate after k pilot-adapter steps" against "incumbent with its current pilot". That is the unrolled or implicit reaction curve.
- **[F2] Why the KL anchor helped play but not decks.** The KL anchor slows the *pilot* (the follower), the opposite of what timescale theory asks for. It made the pilot better on human lists (+65 Elo) without changing the decks. My reading: the decks were still selected by an un-adapted comparison, and the anchor did not touch that.
- **[F3] Compute-frugal unroll.** Fine-tune only a small per-candidate adapter (LoRA or a head) for a few hundred games, cached per archetype cluster rather than per deck. This keeps the "unroll" affordable on one RTX 5070 Ti. This is an engineering inference, not something a paper here tested.

### Gaps
- The convergence results assume smooth, often (strongly) convex inner problems and continuous leader actions. Nothing here covers a discrete design space with a stochastic RL follower, or a population of leaders playing a zero-sum game against each other.
- I found no empirical paper that sweeps the design-update vs controller-update ratio in RL co-design and reports a stability threshold. Cheney 2018 found that the mutation ratio (1:99 to 99:1) alone did not fix premature convergence, which suggests timing without protection or fine-tuning is insufficient.

## Q5. Concrete remedies that would carry to a deck/pilot loop (innovation protection windows, fine-tune-before-judge, per-niche controllers, transfer tests), mapped to F1-F6

### Takeaway
The strongest literature-backed changes are listed below, ordered by fit to the observed failures. Each is game-general and uses no human data. The first three target the root cause the co-design papers identify: new designs are judged by a controller that has not adapted to them.
1. Pilot-adaptation-age protection.
2. Fine-tune before judging.
3. Regret-curated pilot training.
4. Per-niche pilot heads with periodic distillation.
5. Stricter, noise-aware acceptance.
6. A slower deck timescale.

### Cited Findings
- **Age-Pareto protection: works in one lab's soft-robot studies, mixed in another test.** About +47% distance at low resolution (21.717 to 31.953) and about +86% at high resolution (32.575 to 60.728) ([Cheney et al. 2018](https://meclab.w3.uvm.edu/papers/2018_RoySoc_Cheney.pdf)). An unthresholded variant did not fix undervaluation in a fully mapped space ([Mertan & Cheney, arXiv 2508.17464](https://arxiv.org/abs/2508.17464)). A "gross change" threshold (age resets only after a change of more than 20% of voxels) was key at high resolution ([Cheney et al. 2018](https://meclab.w3.uvm.edu/papers/2018_RoySoc_Cheney.pdf)).
- **Fine-tune-before-judge: one optimisation step suffices for transfer tests in two independent systems.** — [Enhanced POET](https://arxiv.org/abs/2003.08536); [Mertan & Cheney 2023](https://par.nsf.gov/servlets/purl/10458459)
- **Transferable or general controllers reduce fragility.** Modular controllers ([Mertan & Cheney 2023](https://par.nsf.gov/servlets/purl/10458459)); controller distillation, "Pollination" ([Mertan & Cheney 2025](https://arxiv.org/abs/2504.06523)).
- **Regret-curated training of the shared learner, with stop-gradient on uncurated designs.** — [Jiang et al. 2021](https://arxiv.org/abs/2110.02439); [Parker-Holder et al. 2022](https://arxiv.org/abs/2203.01302)
- **Fairness or balancing of the shared evaluator's training.** — [FairNAS](https://arxiv.org/abs/1907.01845); [MetaMorph](https://arxiv.org/abs/2203.11931)
- **Multiple partial evaluators instead of one.** — [few-shot NAS](https://arxiv.org/abs/2006.06863); [Luck et al. population + individual networks](https://arxiv.org/abs/1911.06832)
- **Diversity-preserving population dynamics.** Remove the oldest rather than the least fit; use small tournaments ([DERL](https://arxiv.org/html/2102.02202v1)). Admit by minimal criterion plus a novelty measure built from agent rankings ([POET](https://arxiv.org/abs/1901.01753); [Enhanced POET](https://arxiv.org/abs/2003.08536)).
- **Warm-up and high-entropy design distribution before designs move.** Even so, a "safe" do-nothing optimum captured 7 of 8 seeds on one task. — [Schaff et al.](https://arxiv.org/abs/1801.01432)
- **Diagnostics: freeze tests and counterfactual re-training.** Freeze the design at generation g ([Cheney et al. 2016](https://meclab.w3.uvm.edu/papers/2016_ALife_Cheney.pdf)). Re-train controllers on champion designs from a different search ([Mertan & Cheney 2024](https://arxiv.org/abs/2402.09231)).

### Inferences
Each item below is a proposal that maps the cited evidence onto metagame-rl. The project notes should be checked first for overlap with past attempts: type cap, turnover, KL anchor, significance gate and exploiter heads were already tried.

1. **Pilot-adaptation-age protection (MIP for decks)** [F1, F3]
   - Track for each deck the number of pilot updates since its archetype was last grossly changed, e.g. more than 20% of the 60 cards changed, or a change of cluster.
   - Replace "worst decks are replaced" with selection on the Pareto front of (win rate, adaptation age): a deck can be removed only by a better deck with *less* pilot adaptation.
   - Cost: an age counter and a gross-change test.
2. **Fine-tune-before-judge for gross edits** [F2, F3]
   - Before comparing a candidate whose archetype differs from its parent, run k PPO steps of a pilot *adapter* on games with the candidate, mirrored for the incumbent.
   - Accept only if the candidate beats the max of the incumbent's last 5 scores on both direct and fine-tuned evaluation (Enhanced POET rule).
   - Single-card swaps keep cheap direct evaluation.
3. **Regret-curated pilot training (PLR⊥ / ACCEL)** [F2, F4, F5]
   - Score each deck by regret, as in Q3.
   - Keep a replay buffer of the highest-regret decks, plus random decks scored under stop-gradient, and train the shared pilot only on buffer decks.
   - The draft head makes small edits to high-regret decks.
   - Expected effect: the pilot is forced to learn the decks it currently under-plays, such as Trainer-heavy lists, which removes the walls' first-mover edge.
4. **Per-niche pilot heads plus Pollination-style distillation** [F1, F2]
   - K archetype heads over the shared encoder: few-shot-NAS sub-supernets, or Luck-style individual networks with about 10% shared replay.
   - Every N iterations, distil the heads into the generalist and keep the result only where it matches each head.
   - Evaluate decks with max(generalist, own-niche head).
5. **Balanced pilot training** [F2]
   - Sample population and practice games so that deck *clusters* receive equal pilot updates (FairNAS), or weight sampling toward clusters with low normalised performance (MetaMorph E_k^β).
   - Compared with the existing type cap, this changes how training *updates* are distributed, not only who is in the population.
6. **Slow the deck timescale** [F2, F3]
   - Decks move at most once per M pilot updates; candidates are evaluated after an unroll (item 2).
   - Do not slow the pilot itself, since the KL anchor result suggests that does not reach the decks.
7. **Game-general novelty and minimal-criterion admission** [F1]
   - Characterise each deck by its rank-ordered win-rate profile against a fixed panel (PATA-EC).
   - Admit turnover decks only if novel and within a "not too easy, not too hard" band against current decks.
   - Remove the oldest rather than the worst (DERL) to keep lineages alive.
8. **From-scratch runs** [F5]
   - Warm up the pilot on high-entropy random decks before decks move (Schaff, MetaMorph pre-training).
   - Use regret, not raw win rate, as the deck fitness so deck-out piles (low decision complexity) are not favoured by an untrained pilot.
   - Keep the design distribution high-entropy and eliminate clusters on a halving schedule rather than greedily.
9. **Diagnostics, using human lists for evaluation only** [F1, F2]
   - (a) Freeze decks at iteration g, continue pilot-only training, and find the earliest g with no final difference. This measures how early deck search really stops.
   - (b) Mertan-style counterfactual: give equal pilot fine-tuning to a wall and to a human list, then replay the match. If the human list then wins, the collapse is an evaluation bias (first-mover), not a real optimum.
   - (c) Measure "fitness at birth" vs "fitness after k adapter steps" for each accepted and rejected edit, and count wrongly rejected edits, following Mertan & Cheney 2026's undervaluation figures.

### Gaps
- No item above has been tested in a competitive, two-player, imperfect-information card game. The size of each effect here is unknown, and they may interact. For example, protection plus regret curation could flood the population with weak novel decks.
- The literature here offers nothing specific for F4 (search distillation failing in expert iteration) or F6 (turn-limit draws). Those need the search/planning and reward-design literatures, which other researchers cover.
- Compute: per-candidate fine-tuning is the costly part. I found no paper quantifying the cheapest unroll length that removes the bias. AdaControl's "up to 80% less than exhaustive" is the only budget figure, and it is from an unreviewed preprint.
