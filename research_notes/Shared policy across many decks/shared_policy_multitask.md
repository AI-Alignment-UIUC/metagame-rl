# Shared policy vs per-task specialists: multi-task RL evidence for one pilot across ~99 decks

Evidence grades: [T] = full text or table read (WebFetch on arXiv HTML/ar5iv); [A] = abstract only; [S] = search snippet or secondary summary; [M] = memory, not checked this session. Numbers from [S]/[M] are not verified.

## 1. Shared vs per-task skill gap (measured numbers)

### Takeaway
The clearest measured gap is on Meta-World: a single multi-task network does worse than the single-task specialists it replaces, and the gap grows with task count. Our own single-task specialist numbers were not extracted, so the size of the gap on a card game is unmeasured.

### Cited Findings
- Meta-World MT10 / MT50, Table 1 (average max success over tasks, 10 seeds): multi-task PPO 30.5% / 35.4%; multi-task TRPO 31.3% / 21.0%; task embeddings 20.9% / 11.8%; multi-task SAC 68.3% / 38.5% — [Meta-World, Table 1 via ar5iv][T: https://ar5iv.labs.arxiv.org/html/1910.10897]
- Meta-World abstract: the evaluated algorithms "struggle to learn with multiple tasks at the same time, even with as few as ten distinct training tasks" — [arXiv 1910.10897][A: https://arxiv.org/abs/1910.10897]
- Single-task rates are NOT tabulated. Appendix B says SAC "can learn to perform all of the 50 tasks to some degree, while PPO can solve a large majority of the tasks" (3 seeds, no numbers) — [Meta-World App. B][T: https://ar5iv.labs.arxiv.org/html/1910.10897]
- CARE (Sodhani et al. 2021), MT10 random goals: CARE 76.0 ± 6.9 vs PaCo 85.4 ± 4.5; MT50 random goals: CARE 50.8, multi-task SAC 49.3, SAC+FiLM 36.5 ± 12.0 — [PaCo table, supplement snippet][S: https://papers.neurips.cc/paper_files/paper/2022/file/86b8ad667206fb9a52ae575fbf1cd6be-Supplemental-Conference.pdf] (note: PaCo authors ran baselines on Meta-World-V2 with reward normalizer removed, so not a reproduction of published numbers)
- A liner.com summary gives CARE MT10 0.84 ± 0.051 after 2M steps vs SAC+FiLM 0.75, PCGrad 0.72, multi-task SAC 0.49 — [liner.com review][S: https://liner.com/review/multitask-reinforcement-learning-with-contextbased-representations] (unchecked against the paper)
- Reproducibility: PTSL (arXiv 2309.08776) reports it could not reproduce CARE's reported results even with CARE's released code, averaging 10 or 20 seeds — [S: https://arxiv.org/pdf/2309.08776]
- Atari, multi-game: one network on 8 games reached near-expert on 7 of 8 within ~20 epochs (~5M frames), per a review of Actor-Mimic — [S: https://liner.com/review/actormimic-deep-multitask-and-transfer-reinforcement-learning]
- PopArt: one IMPALA-PopArt agent over all 57 Atari games, median human-normalized score reported at 110% vs 59.7% for IMPALA multi-task — [S: https://research.google/pubs/multi-task-deep-reinforcement-learning-with-popart/]; the 110% figure came from a truncated excerpt, so verify in the full paper.

### Inferences
- Multi-task shared policies lose clearly on Meta-World MT10/MT50 against the single-task numbers the field reports, but this was not measured with matched budgets in what I read. Treat the gap as "large and task-count dependent" [A/T mix], not a specific size.
- Whether a shared pilot loses skill on a card game is an empirical question. The Meta-World gap comes from continuous control with different reward scales; transfer to a two-player card game is an assumption.

### Gaps
- No matched single-task vs shared numbers at equal experience budget extracted from [T] sources. The per-task PPO/SAC success rates need the Meta-World appendix tables or the code.
- No card-game or board-game result for shared vs per-deck specialists was found. One AAMAS 2025 Hearthstone abstract (zero-shot to unseen cards with five test decks) was seen only as a snippet [S: https://aamas.csc.liv.ac.uk/Proceedings/aamas2025/pdfs/p2795.pdf]; no numbers read. Another 2026 arXiv Hearthstone-style paper (https://arxiv.org/pdf/2605.28863) was not opened.

## 2. Transfer / distillation / shared-prior designs (cost and when they win)

### Takeaway
The best-documented specialist-plus-shared designs (Distral, policy distillation, kickstarting, Actor-Mimic) all report gains in sample efficiency, but the numerical budgets I could read are for 4-8 tasks with large experience counts. Distral's cost is roughly one extra policy per task plus a KL term, which at our 99-deck scale means 99 specialists.

### Cited Findings
- Distral (Teh et al. 2017): one shared "distilled" policy; per-task workers regularized by KL to it; 8 mazes, 4 navigation, 8 laser-tag tasks, 32 A3C workers per task, 4×10^8 env steps per task for maze and navigation, 6.6×10^8 for laser-tag. Reported results are qualitative (figures only in the text): Distral learns faster and reaches better final performance than multi-task A3C; the two-column variants are best on navigation; on laser-tag the best baseline is single-task A3C — [Distral, full text via ar5iv][T: https://ar5iv.labs.arxiv.org/html/1707.04175]
- Distral cost: each task keeps its own policy, so compute and memory scale with task count. The paper's hyperparameter sweep was 36 runs per algorithm — [T: same source]
- Distral abstract: learns faster, is more robust to hyperparameters, more stable than multitask A3C — [A: https://arxiv.org/abs/1707.04175]
- Kickstarting (Schmitt et al. 2018): teacher-to-student KL-style bootstrapping, with the student free to surpass teachers. On DMLab-30 (IMPALA), the student matches from-scratch performance in roughly 1/10 the steps and finishes 42% higher — [S: https://arxiv.org/pdf/1803.03835] (the 10× / 42% figures are from the abstract as quoted in search results)
- Kickstarting caveat from a reader's notes: the student may ignore an incompetent teacher — [S: https://yobibyte.github.io/files/paper_notes/Kickstarting_Deep_Reinforcement_Learning_Simon_Schmitt__Jonathan_J__Hudson__Augustin_Zidek_et_al___2018.pdf]
- Actor-Mimic (Parisotto et al. 2016): policy regression to expert DQN softmax outputs; the multitask net is then reused to initialize target games, learning faster than from random init. Code notes say the full multitask-to-transfer pipeline can take over 3 weeks on a fast GPU — [S: https://github.com/eparisotto/ActorMimic] (search snippet with repo notes)
- Policy distillation (Rusu et al. 2016) and soft-Q (Teh/Distral) are cited inside kickstarting; I did not open the Rusu paper, so I have no number for it. [M]

### Inferences
- Shared-prior designs need experience on each specialist, so cost is "N specialists × budget" plus a distillation phase. For ~99 decks this is a real cost. Kickstarting-style bootstrapping from a shared pilot is the cheapest variant, but it has the "student ignores bad teacher" failure mode, which matters if some decks are weakly played (the case in our loop).
- Distral's KL-to-shared-policy term is a direct way to stop per-deck specialists from drifting, but its benefit was shown with 4-8 tasks. Extrapolation to 99 is unmeasured.

### Gaps
- No measured experience cost for Distral vs plain shared training at matched total steps was readable here (only per-task budgets).
- Policy distillation (Rusu 2016) numbers: not read.

## 3. Task conditioning: FiLM, soft modularization, CARE, PaCo, attention

### Takeaway
On Meta-World MT10/MT50 with random goals, conditioned or modular methods (CARE, PaCo) beat plain multi-task SAC by a clear margin in the papers' own tables. Those tables come from the authors' setups and have been questioned for reproducibility, so the margin is reported, not confirmed.

### Cited Findings
- PaCo (Sun et al. 2022), MT10 random goals 85.4 ± 4.5 vs CARE 76.0 ± 6.9; MT50 random goals 57.3 ± 1.3 (K=20) vs CARE 50.8, multi-task SAC 49.3, SAC+FiLM 36.5 — [S: PaCo supplement, https://papers.neurips.cc/paper_files/paper/2022/file/86b8ad667206fb9a52ae575fbf1cd6be-Supplemental-Conference.pdf]. On MT10 with fixed goals, PaCo's advantage is smaller, and multi-task SAC can be competitive (appendix note) — same source.
- Soft modularization (Yang et al. 2020): routing network softly combines module paths per task, built on SAC; reported gains over prior routing methods, largest on the harder goal-conditioned MT50 — [A/S: https://papers.nips.cc/paper/2020/hash/32cfdce9631d8c7906e8e9d6e68b514b-Abstract.html; https://arxiv.org/pdf/2003.13661]. I did not read the numeric table.
- CARE (Sodhani et al. 2021): mixture of encoders with attention guided by task context; numbers in §1 — [S: https://ar5iv.arxiv.org/html/2102.06177]
- Kurin et al. 2022 and Xin et al. 2022 (§5) also re-ran SMTO baselines; their point is that the plain baseline holds up against these conditioned/optimizer methods on the benchmarks they tested.

### Inferences
- Deck identity in our pilot already enters through cross-attention, which is the same family as CARE/PaCo. The question for us is whether a deck-conditioned module (soft routing, parameter-compositional) beats concatenation on the same deck set. No head-to-head on a card game was found.
- Important: PaCo and CARE report gains with task IDs or context, but the deck is observed by the pilot, so their designs transfer without human card knowledge. Good: this stays within the human-free constraint.

### Gaps
- Hypernetworks and plain FiLM vs concatenation: FiLM appears only as a baseline (SAC+FiLM). No hypernetwork numbers were read.
- Results on the same benchmark with the same seeds and reward version are scarce. Meta-World v1 vs v2 and goal-random vs goal-fixed settings differ across papers, so do not compare numbers across tables.

## 4. Gradient and return imbalance

### Takeaway
The simple unitary sum of task losses (with standard regularization) matches or beats specialized gradient methods on Meta-World MT10/MT50 in the Kurin et al. study. Xin et al. find the same on language and vision. Return-scale normalization (PopArt) is the one method with clear measured value, on Atari.

### Cited Findings
- Kurin et al. 2022: unitary scalarization (plain sum) performs on par with other SMTOs on MT10 and no SMTO significantly outperforms it on MT50; PCGrad's MT50 average is "slightly above" unitary — [T: arXiv HTML, https://arxiv.org/html/2201.04122, text only, RL results are in figures]. Runtime: unitary ~15 h per run vs more than a week for PCGrad, MGDA, GradDrop on MT50 (same source).
- Kurin et al.: SMTOs behave as regularizers that delay overfitting (CelebA ℓ2 ablation); MGDA and IMTL show larger update norms near convergence, read as under-optimization — [T: same].
- Kurin et al. abstract: summed losses with standard regularization are as good as or better than specialized optimizers in supervised and RL settings — [A: https://arxiv.org/pdf/2201.04122]
- Xin et al. 2022: MTO methods give no gains over standard optimization across large-scale language and vision experiments; they also flag training pitfalls and evaluation difficulty — [A: https://arxiv.org/abs/2209.11379]. Their RL results were not read.
- PCGrad (Yu et al. 2020): paper gives MT10 results only in a figure (multi-head SAC vs +PCGrad); numeric values not extracted — [S: https://arxiv.org/pdf/2001.06782]. A re-run in the PaCo supplement gives PCGrad MT10 fixed goals 81.8 ± 5.2 vs multi-task SAC 84.5 ± 12.4 and CARE 86.6 ± 9.8 — [S, re-run, different setup].
- PopArt (Hessel et al. 2019): scale-invariant value normalization for multi-task actor-critic; IMPALA-PopArt median human-normalized 110% vs 59.7% on 57 Atari games (verify) — [S: https://research.google/pubs/multi-task-deep-reinforcement-learning-with-popart/]
- CAGrad (Liu et al. 2021): not read in this session. [M]

### Inferences
- If our return scales differ by deck (e.g., deck-specific win rates or reward magnitudes), a value or advantage normalization per deck is cheap and matches the one method with measured gains. The Kurin/Xin results say gradient surgery is unlikely to help more than that.
- Reweighting decks by inverse frequency is a "task reweighting" change, and the closest measured evidence is the SMTO comparison above (not a reweighting result). Its effect on deck selection bias is unmeasured here.

### Gaps
- No RL result for PopArt in a two-player or card setting was found.
- CAGrad numbers were not checked; Xin 2022 RL numbers not checked.

## 5. Varied tasks vs repetition

### Takeaway
On Procgen/CoinRun, agents trained on few levels overfit, and test performance rises monotonically with the number of training levels. This matches the advice to train on many varied decks rather than a few fixed ones, but the evidence is about levels in one game, not decks.

### Cited Findings
- Cobbe et al. 2019 (CoinRun), Table 1, 5 seeds, test performance vs training levels (IMPALA-CNN): 100 levels test 66.58 ± 1.91 (train 99.39); 500 → 80.25; 1000 → 84.84; 2000 → 90.92; 4000 → 95.87; 8000 → 97.29; unlimited → 98.29 ± 0.16 (train 98.11) — [T: https://arxiv.org/html/1812.02341v3]
- Nature-CNN: test 66.79 at 100 levels, 90.04 at unlimited; train falls from 99.45 to 90.87 as levels grow — [T: same]
- Paper states "substantial overfitting occurs when there are less than 4,000 training levels" (Nature-CNN) — [T: same]
- Procgen (Cobbe et al. 2020): 16 procedural games, default 500 training levels — [S: https://arxiv.org/pdf/1912.01588]
- Domain randomization: not read. [M]

### Inferences
- The fewer-training-levels-did-worse result here is on test levels. The "fewer repeated tasks does worse even on those tasks" case is the Nature-CNN train column: with few levels the agent memorizes them and train score goes UP; with many levels train score goes down. So a small fixed deck pool can look better in training than it generalizes. That is the overfit pattern to watch for on training decks.
- Cobbe's gap closes only near unlimited levels. 99 decks is far from unlimited, so some train-test gap on new decks should be expected.

### Gaps
- No card-game result on fixed vs varied deck pools was found.
- Procgen per-level numbers beyond Table 1 were not compared.

## Stop-rule note
Tool count: about 23 searches and fetches, within the ~25 limit. Searched in English only. Skipped per the project list: co-adaptation, innovation protection, weight-sharing rank, prioritized level replay, deck search, tempo/draw value, exploration.

## Sources read in full [T] vs abstract or snippet [A/S]
- [T] Meta-World (ar5iv), Distral (ar5iv), Kurin et al. 2022 (arXiv HTML, text only), Cobbe et al. 2019 (arXiv HTML, Table 1).
- [A] Meta-World abstract, Distral abstract, Kurin abstract, Xin abstract.
- [S] everything else (PaCo, CARE, PCGrad, kickstarting, Actor-Mimic, PopArt, Procgen, Hearthstone AAMAS, soft modularization).
