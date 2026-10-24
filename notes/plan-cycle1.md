# First-cycle plan (cycle 1), 2026-10-22

Built from the 44 reviewed candidates C01-C44 (`notes/data/cycle1/candidates.json`, with every review) under `notes/method.md`. Every candidate survives the review rule: none has
a reject on any angle, so nothing is parked for failing review. Candidates are parked here only for cost, missing
prerequisites, or a dependency on Evan.

**How the plan was ranked**
- **Measure:** information per desktop-hour (dh: screen slot-hour 1, GPU probe-hour 0.5, CPU probe-hour 0.25,
  agent-hour 1). Information means the Q1 rivals (E game, I inputs, P pilot, J judge, S selection, X exploration) that
  a candidate can demote.
- **Order:** upstream links (E, I, P, J) come before S and X on ties.
- **Floor (§8):** a prevention start sits among the first four screens, every live rival has a queued candidate, and
  at most 2 of the 3 slots run the incumbent lineage.
- **Reviews:** every portfolio item below carries its reviewers' required changes. The changes that alter the design
  are written into each item.

**Machine:** the desktop is idle (GPU 1.3 of 16.3 GB, no screens). The limits are:
- at most 3 screens, each about 2.7 GB RAM and 3.5 GB GPU;
- a GPU probe (RL_GPU_SHARE about 0.15) only beside at most 2 screens;
- one CPU probe (4 workers) beside them;
- C03's searched path only while at most 2 screens are live.

Engine and runner edits must be opt-in with default off, and they land between screen batches. A seeded trace-hash
check (rule-off games identical) runs before any running screen's workers restart.

**Spend (the cheaper spend Evan chose):**

| Tier | Items | Cost |
|---|---|---|
| A, core | 1-10 | about 35 dh, about 1.5 days elapsed |
| B, stretch | 11-14 | about 29 dh; may spill into cycle 2 without loss |
| Conditional | 15-16 | about 18 dh, only if their gates fire |

The agent lane is the bottleneck, not the GPU.

## 0. Before any launch

Clear the log debt first (§13: no launch while a finished result is unlogged). `runs/lab/STOP` and README Next already
cite log #150 and `notes/method.md`, but neither exists yet. The steps are in §6 (declutter now), items 1-3.

## 1. Portfolio

dh = desktop-hours. Rivals use Q1's set (E, I, P, J, S, X) plus each candidate's own named rivals. Bands are
pre-registered and include the review changes.

| # | Id: item | Slot | Cost | Rivals (Q1) | Predictions (bands) | Readout | Kill rule |
|---|---|---|---|---|---|---|---|
| 1 | **C09** Open decklists, step 1 | GPU probe, beside ≤ 2 screens | 0.5-1 h code + 15 min GPU (≈1 dh) | I: R1 leak / R2 irrelevant / R3 out-of-distribution / R4 symmetric use | R1: asymmetry A = 2S_shown − S_wallsHidden − S_listsHidden ≥ 0.05, and the decoy list hurts the walls as much as hiding. R2: both seat effects ≤ 0.03 with 90% upper bounds < 0.05. R3: each single-seat mask costs its own seat > 0.10 while the decoy costs ≈ 0. R4: both effects > 0.03 and equal | Walls' verdict in 5 arms (shown, hidden from walls, hidden from lists, hidden from both, decoy), 1,152 games each on #147 deals; cluster bootstrap over the 24 lists; endings | Close as R2 by the CI rule; 0.03-0.05 → one more deal seed; step 2 only under R1/R3, on the C08/C35 testbed (cycle 2) |
| 2 | **C07** Zero-training judge zoo | GPU probe, beside ≤ 2 screens | 1.5 h script + 1.5-2 h GPU (≈2.5 dh) | J1 exposure vs J2 payoff; familiarity; H19 human side; I count bug / open lists; encoder; null | Payoff: w1 − w0 ≥ 3 paired SE (≈ 0.08) with w1 ≥ 0.55 and ≥ 50% deck-out wins, and high verdicts persist in ≤ 40-turn games. Exposure: every wall-naive pilot ≤ 0.40 and w1 − w0 within ±0.05. Familiarity: the a4-tok family ≤ 0.35-0.40 while abl ≥ 0.55. H19: walls 499 + lists a4-tok ≤ 0.55 opens the lever, ≥ 0.65 closes it. Count bug, no-deck and encoder: shift ≥ max(0.05, 2√2·σ_seed) at it19 and it39 | Walls vs 24 lists per judge and pairing; within-pair differences against the 8-pair seed band; skill and speed covariates; ≤ 40-turn score; human-free twin vs `wide12` | Probe base-cont it39, ent-cont it39 and base-s2 it79 first. If none clears the seed band or 0.55, stop the abl sweep. Drop a judge with > 2% errors or caps. Do not read a pair whose pilots differ by > 0.1 vs SimpleBot. Item 16 (C17) only if (b) lands in exposure, familiarity or 0.40-0.55 |
| 3 | **C13** stage 1: exact STS rule on all 24 lists, wall sets B and C, the J2 linchpin replication, walls-only seat | CPU probe (`walls_vs_humans.js`, 4 workers) | 1.5 h agent + 6 CPU-h (≈3 dh) | E / ExP / P / Plateau / Imbalance (the subset-artifact rival is dropped) | Set A J1 is already measured: W(T) 0.48-0.58 at T 20-45, which decides ExP's J1 clause; B and C are blind. **E:** W(J1, Π) ≤ 0.55. **ExP:** ≥ 0.58. **P:** J2 clockless all-24 < 0.50 (subset prior 0.648). **E+P replicates:** J2 at T 50-60 ≤ 0.50 with 90% CI < 0.55. **Plateau:** W(J2, Π) ≥ 0.52. **Imbalance:** walls-only gain ≤ 0.02 vs human-side ≥ 0.10 | Primary: break-even turn T50 per judge and set (bootstrap by wall-list pair). Then W(J, T) curves (untimed, plain draw, exact STS at T 20-80), per-list equal weights, the Energy axis (C vs B) and wall wins by ending | Stop J2 all-24 after 192 new games if clockless < 0.48. Stop the walls-only cell after 192 games if the upper 90% bound of its gain is < 0.05 (SE from the 0.573 / 0.648 rerun spread). J2 on B/C, J3 and level 2 wait for item 11 |
| 4 | **C33 + C40** one decision message to Evan | Agent, then Evan | 1 h (≈1 dh) | Safety-net vs specification reading (C33); R-allowed vs R-prior (C40) | Specification: C34 opens with T fixed by D2. Safety net: the walls' edge must go through pilot or judge strength. Allowed: C41's kind-aware cells become method candidates. Prior: they stay diagnostics and W retrains on flat decks | Each answer logged in `evan-requests.md`, with the action for every answer (including a conditional yes) written in advance | No C40 answer within a day: C41 runs as a diagnostic at the game-agnostic level. No D1 answer: the rule stays evaluation-only |
| 5 | **C29** A/A of the gate recipe at 479, reseeds 3 and 4 | 2 screen slots | 3.5 slot-h + 0.5 GPU-h + 0.5 h (≈4.5 dh) | S/measurement: H-noise / H-attractor; gate real vs luck | **Noise:** pooled 3-df SD upper bound ≥ 3 cards (window distance) or ≥ 10 wall-core decks, so arms inside it become inconclusive. **Attractor:** ≤ 1.5 cards and ≤ 5 decks. 1.5-3 cards or 5-10 decks: inconclusive, keep the 2.0-4.8 band. **Gate real:** the Welch 95% CI of gated − ungated largest type excludes 0 and its bound nearer zero is ≥ 20 decks below | Pairwise per-iteration RMS over the 3 gated pairs, pooled with ctl479 vs resetcap; wall-core decks (Chansey+Snorlax) at 484-499 primary; overlap type secondary; final-pilot walls verdicts | None (A/A); a crashed run is resumed. Claims are limited to "are the 479 arm nulls real nulls" |
| 6 | **C30** Pilot-first warm-up W (prevention start) | 1-2 slots (`rl.train`, about 6 workers each) | 0.75 h code + 5 slot-h + 2 CPU-h eval (≈6.5 dh) | Bootstrap ok vs stall; judge by-product H5 vs H1 (J) | **Ok:** criterion by it ≤ 40 in both seeds. **Stall:** deck-outs ≥ 50% and prize endings ≤ 30% at it40. **H5:** JF1(W) ≥ 0.55. **H1:** ≤ 0.35. Both read only when W is within about 30 Elo of pilot-v2 on the lists. JF1 rising with competence means stall was learned; falling means low skill | Endings per iteration for 2 seeds; JF1 and h2h vs pilot-v2 (lists and held-out wide decks) at it20, it40 and the end; JF2 at the end only, as a sanity check | ≥ 50% deck-outs at 60: bootstrap failed, start the margin fallback (C35's code). 25-50%: continue to 90. JF1 in 0.40-0.55: third seed, or the better seed to about 120 |
| 7 | **C14** Draw-seeking check of the turn-limit runs (Evan rows 24-25) | GPU job, counted as 1 slot | 1.5-2 h code + 1 GPU-h (≈2.5 dh) | E: D0 shared drift / D1 pilot draw-seeking / D2 deck draw-seeking; D3 caps reported apart | Components are measured against an anchor cell (the 479 decks and pilot). **D1:** pilot effect ≥ 10 points at limit 40, with behind − ahead attack/draw-Trainer gap ≥ 0.10 near the limit (no asymmetry means competence loss). **D2:** deck effect ≥ 15 points tracking Pokémon count. **D0:** both effects < 5 points. A component counts if ≥ 1/3 of the rise and > 3 SE (pair-clustered) | Limit-ending share per cell (2,000 games); deck, pilot and interaction effects; Prize difference at the limit; per-side behaviour by Prize state and turns left (1-3, 4-8, 9+); limit 70 at 489 and 494 | Stop if the own-by-own cell misses its logged limit share by > 5 points, or no cell gives ≥ ½ of (own − anchor). Cap trace: stop at 50 capped games with no sequence repeated ≥ 3 times |
| 8 | **C02** Outside research on the specification | Agent (deep-research subagents), no machine | about 5 agent-h (≈5 dh) | E premise: R-fast / R-slow / R-unknown; H-pilot-slow as a separate axis | **R-fast:** 20-50 engine turns a round, time called often, few deck-outs, so T prior ≤ 50. **R-slow:** 60-70+ turns or time rarely reached. **Pilot-slow:** human Haymaker/Wigglytuff wins in 12-20 engine turns vs our 34-41. **Unknown:** < 2 independent sources, so C13's whole curve stands | A table per question (answer, quotes, number of sources, confidence, the decision it feeds) | 4 h box plus 1 h quote check; 45 min per question without a primary source → "unknown"; outside data on which decks won never sets a parameter |
| 9 | **C24** Draft-head bench, null vs planted rewards | GPU probe (head-only) | 3 h code + 1 GPU-h (≈3.5 dh); stage 2 +3 dh | S: H-drift / H-signal / H-overreact / H-view | **Drift:** null h_in ≤ 1.5 by step 12 in ≥ 4/5 seeds (≥ 60% of the parameter part of ctl479's fall); cut Trainer share ≥ 1.15× copy share. **Signal:** null h_in ≥ 2.5 through step 20, cut 1.08 ± 0.03, first collapse at δ in [0.01, 0.03]. **Overreact:** collapse at δ 0.005 with KL per update unchanged from 0.005 to 0.05. **View:** most of the logged fall is deck-distribution | h_in and h_out per step against the split of the logged fall; cut Trainer share; steps to h_in < 1 by δ; KL vs SNR; measured seed SD | Fixed plan. Null at 1.5-2.5 nats, or seed SD > 0.3 near a band edge, sends the question to C25 (item 15). Skip stage 2 under H-signal with δ* ≥ 0.01 |
| 10 | **C08** step 1: attached-Energy count bug sensitivity | GPU probe (forward passes) | 4-6 h agent + minutes GPU (≈5 dh) | I: R1 distorts / R2 inert / R3 opposite channel | **R1:** probe accuracy drops on Bench, opposing slots and rare (slot, copies) codes; ≥ 3% flips on Energy decisions; normalised Energy-swap \|dV\| ≥ 0.5 vs positional baseline ≤ 0.2; concentrated on own Bench, attach and retreat. **R2:** flat accuracy, < 1% flips, ratios ≤ 1.3. **R3:** concentrated on opposing ENERGY tokens and ER/SER targets | Probe accuracy by slot class and code frequency; count-input ablation vs a matched HAND-count control; metamorphic swap ratios with bootstrap CIs | Stop after step 1 under R2. Step 2 (fix plus 2 bug students, ≥ 2 seeds, human-free non-inferiority) goes to cycle 2 under R1/R3 |
| 11 | **C03** GPU-served searched probe with CRN | Infrastructure; GPU only with ≤ 2 screens live | 6-8 h code + 1-2 GPU-h (≈8 dh) | J/P measurement: same vs different judge; re-deal noise vs CRN-null | **Same:** CPU-GPU decision agreement within 2 SE of GPU-GPU. **Different:** > 2 SE below. **Re-deal:** independent self-agreement ≤ 0.65 and CRN ≥ 0.80, off-top down ≥ 25%. **CRN-null:** independent ≥ 0.80. 0.65-0.80 = partial (C37 only at CRN ≥ 0.80) | Decision-level parity on ≥ 500 positions; CRN manipulation check; self-agreement on 2,000 human-free positions (game-clustered SE); #147-matched arm (a) as a gross check, flagged at > 0.15 | Different judge: debug before any searched use. Independent agreement ≥ 0.85: keep current search. Drop CRN if the agreement gain is < 0.05 and the changed share moves < 0.05. Drop k8 d2 if line errors > 1% |
| 12 | **C10** Human-field tempo ladder and competence panel | GPU + CPU probes | Stage 1 ≈ 4 dh; stage 2 ≈ 5.5 dh (≈9.5 dh) | P: R1 in-turn / R2 beyond-turn (objective vs horizon split) / R3 deck-resource myopia | Primary: searched − greedy on the 499 pilot, tempo-vs-tempo stratum. **R1:** pace +≥ 0.5 Prizes by turn 20 and deck-outs −≥ 5 points. **R2:** pace < 0.2 and deck-outs within ±5, with search shown working. **R3:** pace +≥ 0.5 and deck-outs flat or up, more draw-Trainer plays. Full pace × deck-out decision table | Unconditional pace (Prizes by turns 10/20/30, restricted mean time to the 6th Prize); deck-outs by pair type; endings split (deck-out winner behind on Prizes?); line-scored puzzles by class with cluster SEs; ctl479 rung as the fork band | Searched rung stops at 512 games if deck-outs are within ±3 and pace within ±0.2 (R2, only if the instrumentation check passes). CRN rung only if C03 shows CRN matters |
| 13 | **C35** Prize margin as the pilot's terminal reward | 1 slot (one training process, arms in sequence) | 1 h code + 1-2 h testbed + 2 slot-h + 1.5 GPU-h (≈6 dh) | P/N10: R1 objective / R2 competence / R3 margin pays the walls | **R1:** human-vs-human deck-outs −≥ 5 points, pace +≥ 0.3 Prizes by turn 20, walls verdict −≥ 0.04 (mostly the lists' seat), ordered by dose, Elo ≥ −15. **R2:** inside \|A/A gap\| + 2·SE_diff (≈ 2.1 points; walls ±0.035), read only if the manipulation check passed and doses agree. **R3:** pace up, walls flat or up, wall deck-out wins keep Prize leads (109/148) | C10 tempo panel; walls verdict with 2×2 seat decomposition; Elo vs control; manipulation check (win margin, deck-out share, value-margin correlation per iteration) | At 10 iterations stop only if the training ending mix and the win margin are both inside the A/A arms; otherwise run to 20. Elo < −40: stop at once |
| 14 | **C28** Valley test along block-wise edit paths (greedy stage) | GPU probe | 3 h builder + 4-5 GPU-h (≈5.5 dh) | X: H-valley vs H-open (H-judge-blocks dropped as already decided) | **Valley:** on J1 and field (a), every order including the greedy best-next-block dips below the chord beyond the null's 95th percentile, confirmed on fresh deals (≥ 576 games). **Open:** each step's gain clears the gate's minimum detectable gain (about 0.11-0.16 at z 1 and about 20 games), or ≥ 1 expected gate pass per step | f(k) along paths for J1 and pilot-v2 on fields (a) and (b) with common deals; bias-corrected dip; expected gate passes; #127 sanity (pilot-v2 rises at the first Pokémon-swap step) | No early stop for greedy judges; the searched J3 subset waits for item 11 |
| 15 | **C25** (conditional) frozen and null-reward head forks from 479 | 2 slots (+1 for F0r) | 1.5-2.5 h code + 4-6 slot-h (≈6 dh) | S: H-amplifier / H-judge-alone / H-S-intrinsic / H-encoder | **Amplifier:** fixed-panel prop \|Pokémon\| < 0.3, Chansey+Snorlax ≤ 60 at 499 vs control-like 73-80, median Trainers ≥ 27. **Judge-alone:** F0 tracks the control with acc − prop ≥ +0.8 Pokémon. **Intrinsic:** N0's h_in falls as fast as the control's with fixed-panel prop ≥ +1. **Encoder:** F0's prop drifts while F0r's stays < 0.3. 61-69 = partial | prop, acc and acc − prop per iteration; fixed-reference prop (current head with the current and with the frozen 479 encoder); h_in; Chansey+Snorlax and median P/T/E at 484-499 | Both forks run to 499 unconditionally. Stop F0 at 489 only if its fixed-panel prop already matches the control's drift (the freeze did not hold) |
| 16 | **C17** (conditional) wave 1: matched pilot-v2 fine-tunes (payoff × field) | 3 slots (about 6 workers each) | 2.5 h code + 8-10 slot-h (≈12 dh) | J: payoff / exposure / familiarity / interaction / incumbency / slow accumulation | **Payoff:** W1 ≥ 0.50, P1 ≥ 0.55, P0 ≤ 0.35. **Exposure:** P0 ≥ 0.50, W1 ≤ 0.35. **Familiarity:** W0 and W1 ≥ 0.45 and P0 ≥ 0.45. **Slow accumulation:** P1 ≤ 0.40 at 40. Decisive contrasts P1−P0, W1−W0 and P1−W1 as paired CIs, bar ≥ 2 pair-clustered SE (≈ 0.07) | Verdict learning curves at 0/5/10/20/30/40 (1,152 games each); human-free twin; walls' ending mix; Elo vs pilot-v2 | Each arm stops at 40, or earlier if h2h on wide decks falls > 60 Elo or caps exceed 2%. P1 < 0.45 at 40: extend P1 to 80. W0 runs whenever W1 rises ≥ 0.10. Seed-2 of P1 and P0 runs regardless |

### Item details (design as revised by the reviews)

**1. C09, step 1.**
- **Masking:** the per-seat hide is done in the model, not the environment. TokenPointerNet.encode masks only
  OPP_DECKLIST (kind 10) tokens and keeps MY_UNSEEN. It runs through `probe_matchups.py`'s per-deck `--pilot` /
  `--pilot-b` slots.
- **Test:** a `rl/tests.py` check that outputs ignore kind-10 tokens when the flag is on and still respond to
  MY_UNSEEN.
- **Shown arm:** reuse `runs/probe/judge/resetcap499.json` as the shown-to-both arm, and rerun it once as a
  determinism check.
- **Decoy arm:** a wrong, in-distribution list given to each seat.
- **Turn limit:** none in the primary arm. Log the deck-out share and length per arm.
- **Analysis:** pre-register the asymmetry and interaction estimands. Power comes from the measured discordance rate
  (likely 60-75% for 0.05, so 0.06 is the detectable effect).
- **Caveats:** the count bug is present in every arm. Adopting hidden lists in training is Evan's call (§4, item 9).

**2. C07.**
- **Before the sweep:**
  - strict-clean `load_state_dict` for every checkpoint, with failures sent to the ONNX/`walls_vs_humans.js` path;
  - a per-game dump in `probe_matchups.py` (i, j, seat, winner, ending, turns);
  - `runs/probe/wide12.json` written from a fixed seeded full-pool draw before anything is read;
  - #139's label corrected after the games are played (a no-Pokémon win against an empty deck is not a deck-out).
- **Primary payoff contrast:** deckout-w1 vs deckout-w0 at 64-96 games a pair, with the it4/it9/it14 dose-response
  and a bootstrap paired SE.
- **Seed band:** all 8 seed-pair differences (base/base-s2 and explore10/-s2 at it19/39/59/79).
- **Architecture contrasts:** replicated at it19 and it39.
- **Covariates:** skill (SimpleBot on the archived lists) for every checkpoint; speed (median turn of the lists' Prize
  wins); exposure (share of training games against Snorlax/Chansey decks).
- **Trends:** within-lineage only; no pooled Spearman cut-offs.
- **Labelling:** pilot-scratch is a replicate of pilot-v2's deck-out-0 condition, not independent payoff evidence. A
  w1 − w0 within ±0.05 leaves the from-scratch deck-out 0/1 pair open.
- **Run settings:** RL_GPU_SHARE 0.15 and 4 workers; about 1.5-2 h beside two screens.

**3. C13, stage 1.** *Done (log #156): E+P replicates on all 24 (J2 at T 50-60 0.492), P and Plateau refuted, Imbalance
holds, E holds for A only; J2 on set C added as a CPU cell (`runs/probe/C13-stage1b/record.md`).*
- **Reuse:** `sts_greedy_all24.jsonl`, `sts_search_human_sub.jsonl` and `sts_search_both_sub.jsonl` are not replayed.
  Their result goes into log #150 first.
- **Finish:** the 26 missing both-seat subset games (minutes).
- **Wall sets:** extract B (`scr-gate479` 499) and C (main `seg_0460`), each the 3 best decks by the population's own
  judged score.
- **Greedy exact-rule curves:** 576 games each for B and C over all 24 lists, plus g8-15 for A (16 a pair).
- **Walls-only k4 d4:** A's 576 deals, with psearch on the walls and greedy on the lists.
- **J2 on all 24 (one deviation from the feasibility review's staging):** J2 both-seat k4 d4 on A's remaining 384
  all-24 deals, about 2.5 CPU-h. Method §4 requires the linchpin row (E+P: 192 games, about ±0.10) to be replicated
  before anything builds on it, and this cell costs CPU hours, not the 25-35 h of the full searched set.
- **Weights:** "field-weighted" means equal weight per list over all 24.
- **Re-registration:** predictions are written against the existing exact results.
- **Primary readout:** T50, the turn at which W(J, T) crosses 0.5, with a pair-clustered bootstrap. It is compared
  with C02's interval later; the prior Π does not decide the verdict.
- **Fallbacks:** the scorer is `walls_vs_humans_report.sts_points` (or this session's `c13_sts.js`). Level 2 needs new
  nested search in PolicySearchAgent (2-4 h). It and the invasion readout go to cycle 2.

**4. C33 + C40, one message.**
- **Framing:** a follow-up to rows 24 and 26. It asks only the never-asked parts: D1 (a') judging-only and (a) with the
  new exact-rule evidence; D2 only if either is approved; D7 commit; engine fixes. C40 Q1-Q3 are asked with their
  constants disclosed and a game-agnostic warm-up criterion offered.
- **Not asked:** D1(b) (evaluation use needs no approval). D3, D5 and D8 are decided in the loop and logged. D6 is
  held until C09 reports.
- **Evidence:** cited from the log now (#63, #71, #124, H27, #139, #147, #150), not after C23 or C30. The exact
  questions are in §4.

**5. C29.** *Done (log #153): the noise band holds as registered; the gate's shape effect replicates, its type effect
misses the registered 20-deck margin; S36 in `notes/hypotheses.md`.*
- **Launch:** from the exact command at the top of `runs/screens/scr-gate479/stdout.log`, changing only `--run` and
  `--reseed`.
- **Config check:** diff each `config.json` against scr-gate479's before reading; only run, reseed and stop_file may
  differ.
- **Snapshots:** `--keep 5`, so they land on 484/489/494/499.
- **Extra cost:** the two final-pilot walls verdicts.
- **Matched control:** C29-s3 is also the matched control for item 15 (same fork, recipe, code hash, workers and
  `--reseed 3`).

**6. C30.** *Done for the bootstrap (log #157): criterion at iteration 8-9 in both seeds, no stall; W is level with
pilot-v2 on wide decks and about 470 Elo below on the lists, so H5/H1 wait on W2's continuation (`runs/pilot/C30/record-cont.md`).*
- **Decks:** `notes/scripts/pilot_decks.py` switched to the full 277-card pool and `rl.decks.wide_deck` (512 decks,
  2,048 pairs).
- **Command, flags written in full:** `--model tokens --d 256 --tok-layers 4 --heads 8 --deck-mode cross --lr 2e-4
  --epochs 2 --ent 0.01 --lam 0.95 --gamma 1 --shaping 0.1 --shaping-iters 100 --deckout-win 1`. The `rl.train`
  defaults are pre-adoption.
- **Stop:** an ending-share monitor applies the stop criterion.
- **Count features:** off, which avoids the live bug. This confound with C41's pilot factor is recorded unless C08's
  fix is applied to both.
- **Prior:** C07's JF1 on the abl deck-out-1 pilots. The method status of `wide_deck` waits on C40 Q3; the run is a
  diagnostic meanwhile.

**7. C14.**
- **Plumbing:** `max_turns` in `GpuMatrix.play` plus a `--max-turns` flag, and a driver that pulls decks from
  `population_it*.pt` with one shared pair list (`pair_keys`).
- **Calibration:** each run's own cell must reproduce its logged limit-ending share (about 93% at limit 40) within 5
  points before effects are read.
- **Logging outside C01's critical path:** the D1 behaviour rates are logged inside the replays.
- **Cap trace:** recast as a separate cap/A6 diagnostic, using option-key logging for games that end capped in sampled
  play. The scr-jsearch479 search-line trace is dropped.

**8. C02.** *Done (log #164): R = 1,200 s and the time procedure documented, s not (R-unknown), so T stays uniform 20..45; H-pilot-slow supported (humans about 13-14 engine turns to six Prizes); `reports/C02-round-length/findings.md`.*
- **Seeding:** Q1, Q4 and Q5 start from what the repo holds (#139's STS page, `notes/sts-2000-engine-check.md`, the
  MTR citations in `research_notes/degenerate-env.md`).
- **Pre-registration:** the formula T = (round seconds − overhead) / (seconds per engine turn) as a range, and its
  mapping to C13, C31 and C34, are written before reading.
- **Order:** Q1 and Q2 first (≥ 2 h), Q4 next, Q3 only after T is recorded, Q5-Q7 with leftover time.
- **Q6:** identification only.
- **Logging:** outcomes are logged as tried rows for H03's and H61's outside-research variants.

**9. C24.**
- **Script:** copy `op_audit.py` (§6, item 7).
- **Optimizer state:** load `population_it0479.pt` with the snapshot's draft optimizer (Adam step 20 restored, as the
  forks did). A fresh-Adam arm is a separate factor.
- **H-view arm:** the frozen 479 head on ctl479's 484-499 views, and ctl479's saved heads on the fixed 479 views. This
  splits the logged h_in fall into a deck part and a parameter part, and the bench is compared with the parameter part.
- **Dose predictions:** disjoint at 0.005, written before running. Given #92's real 0.006-0.03 effects, a collapse at
  0.005 is read as overreaction only if the KL per update does not scale with SNR.
- **Stage 2:** 2-3 h, only under drift or overreaction. It includes C42's random-one credit control.

**10. C08, step 1.**
- **Swaps:** done in token space (SLOT positions 1-12 with their feature rows, the slot index inside UNDER/TOOL/ENERGY
  aux, the +1-Energy edit in both copies and `slots[o+10]`).
- **Ablation:** only the `count_features` / `count_proj` input of ENERGY tokens; the 256-way aux embedding is kept.
- **Reference:** `031-pilot-slotbind-w` is a ratio control only (its owner embeddings move Energy-free swaps too).
- **Step 2:** if R1/R3 hold, step 2 adopts only on human-free non-inferiority. Human-vs-human tempo and the walls'
  verdict stay diagnostic.

**11. C03.** *Cost approved by Evan (row 41, "Sure re cost"); next on the agent lane after C02's T.*
- **Plumbing:** `judgeSearch` passthrough, per-job search flags and `searchStats` in `rl/gpu_matrix.py`.
- **CRN:** one seed per determinization, drawn outside the options loop in PolicySearchAgent (`env/agents.js:377-380`),
  under an option flag. The tsearch CRN is a separate edit in `remote_worker.js`.
- **Tests:** k = 1 replays greedy exactly; identical options score identically under CRN.
- **Arm (a):** matches #147 exactly (maxTurns 0, maxSteps 40, h1, both seats, `walls_vs_humans.js` seeds).
- **Gates:** adopting CRN in the judge or in EI targets rests only on human-free positions. Lines are compared at
  matched realised counts.
- **Machine:** it runs with ≤ 2 screens live, or counts as a slot.

**12. C10, staged.**
- **Stage 1** (needs no C03):
  - instrumentation: per-seat Prizes at game turn 20 in the runner and remote rows, a per-game dump, Trainer plays by
    class, explicit mirror pairs;
  - rungs: SimpleBot, pilot-v2, resetcap 499 and ctl479 499, all greedy; 1,024 games each on fixed seeds;
  - the decision table written down.
- **Stage 2:**
  - the searched rung (C03 path, or CPU overnight with about 4 workers);
  - puzzle regeneration, timed on one 400-game part first with `--max` above 300;
  - a line-scored mode with fixed coins both ways, adversarial opponent decisions, UNPROVABLE handling and an oracle
    self-check;
  - a slot-bind rung if a comparable checkpoint exists; otherwise R2 is reported with the count-bug caveat.
- **Use of panel scores:** they rank pilots between runs and are never an in-run selection input.

**13. C35.**
- **Reward code:** in `env/runner.js` `finish()`, `left()` moves before the reward loop. Reward = (1 − w)·result +
  w·(Prizes taken − conceded)/6 for every ending. w is threaded through every Runner construction in
  `remote_worker.js` and through the train/metagame flags. `aux_targets` is decided explicitly.
- **Unit test:** fixed endings (6-0 Prize win, deck-out win while leading, deck-out win while behind, draw).
- **Testbed:** human-free, built here unless C08's step 2 builds it first: the 499 population, other types from
  snapshots, and wide decks. Every flag of the 499 pilot is pinned.
- **Arms:** control w = 0 in two seeds (the testbed A/A), w = 0.5 and w = 1 (required). Evaluation uses common seeds.
- **Readout:** the walls' deck-out-win Prize-lead share per arm.
- **Prerequisite:** item 12, stage 1 (the tempo panel).

**14. C28, greedy stage.**
- **Paths:** whole evolution lines, with 7-8-card lines split basic-first, so every step is ≤ 6 cards and leaves no
  orphan evolution. Each step's realised P/T/E is logged.
- **Endpoints:** the 3 resetcap 499 walls → 3 human targets, with endpoint games kept apart from selection games.
- **Orders:** 3 fixed orders plus a greedy best-next-block order.
- **Judges and fields:** J1 (499 greedy) and pilot-v2. J1 on the walls-heavy field (a) is the primary cell.
- **Precedent:** cite #127's two hybrids and do not re-spend games on them.
- **Generality:** any operator that follows from H-valley must define blocks game-agnostically.
- **Machine:** about 8-12 games/s on wall games, so about 2-2.5 h per judge beside the screens.

**15. C25 (gate: C24's null arm ends in 1.5-2.5 nats, or seed noise leaves it unresolved).**
- **Arms:** F0 `--draft-lr 0` and N0 `--draft-null` (rewards permuted across draws within an iteration; about 20
  lines), both with `--reseed 3` against C29-s3.
- **Proposal readout:** the fixed-reference prop scorer (about 1 h, offline over saved snapshots) and/or F0r
  (`--draft-reader-frozen`, about 30 min).
- **Flags:** scr-gate479's flags written in full.

**16. C17 (gate: C07 (b) in exposure, familiarity or 0.40-0.55).**
- **Ending label:** the fix ships as an opt-in flag, applied only when no screens are live. pilot-v2's iteration-0
  verdict is re-measured under the fixed label as the baseline.
- **Settings:** workers set per arm (about 6); every PPO flag written out; matchup builders as designed.
- **bal-1:** checks first that the Chansey/Snorlax walls fall in one cluster and that ≥ 3 non-wall clusters exist.
- **Labelling:** P1 is a positive control, not a new judge-sweep point.
- **Status:** quarantined diagnostic. Whether a pilot-v2 descendant may become a method component is Evan's call
  (§4, item 6).

## 2. Schedule by lane (respecting the 3-screen, 80% caps)

| When | Screens (≤ 3) | GPU probe (beside ≤ 2 screens) | CPU probe | Agent |
|---|---|---|---|---|
| Hour 0 | C29-s3, C29-s4 | C09, then C07 | C13 stage 1 (finish the subset, B/C greedy, walls-only, J2 all-24) | §6 declutter and log #150; C09/C07 scripts |
| Hour ~2 | C30-W1, C30-W2 | C24 bench | C13 continues | C33+C40 message; C02 launched as a parallel deep-research run |
| Hour ~5 | C14 replays (1 slot); C25 F0/N0 if gated (2 slots, reseed 3) | C08 step 1 | C30 JF1/h2h evals | C14, C08, then C03 |
| Day 2 | C35 arms (1 slot); C17 wave 1 if gated (3 slots, so no GPU probe meanwhile) | C03 validation (only with ≤ 2 screens live); C10 rungs | C10 puzzle generation | C10, C35 |
| Day 3 | C17 seed-2 and W0 if needed | C28 greedy | C10 searched rung (CPU fallback) | C28; log; close the cycle |

Runner and environment edits land between batches: C10's instrumentation, C35's reward and C14's `max_turns` are
opt-in and default off, each checked with a trace hash.

## 3. Floor, coverage and the Matrix

- **Prevention start:** C30 W1 and W2 are two of the first four screens. That covers the start-class gap; 25 of 27
  past screens forked wall states.
- **Coverage gaps off the leading rival's nodes:**
  - N9 bootstrap (C30);
  - the cut choice (C24);
  - the Energy-count input (C08);
  - open decklists (C09);
  - unfinished-game payoff (C14, C13);
  - target validity (C02);
  - prompt decisions and who decks are scored against: queued for cycle 2 (C11, C20).
- **Incumbent lineage:** at most 2 of 3 slots (C29 or C25 beside C30, C14, C35 or C17). 479 forks are at most 4 of
  about 11 screen runs this cycle.
- **Every live Q1 rival has a candidate that can demote it:**

| Rival | Candidates |
|---|---|
| E | C13, C14, C02 |
| I | C09, C08, plus C07's arms |
| P | C10, C35 |
| J | C07, C30's JF1, C17 |
| S | C24, C29, C25 |
| X | C28 |

- **Leader first:** the leader is the E+P conjunction (#147). It is attacked first by C13's blind B/C cells and the
  all-24 J2 replication.
- **Routing after the cycle:**

| Result | Next |
|---|---|
| C07 payoff | Judge work goes to strength plus the cut (C13 stage 2, C20, C38); C39 closes |
| C07 exposure or familiarity | C17, then C39 |
| C08 or C09 under R1 | A fix before any further judge result builds on the inputs |
| C10 R1 | C37 and C38 |
| C10 R2 | C35, C36 and C12 |
| C24 signal | Head work stops |
| C24 drift | Stage 2 fixes and C42 |
| C28 valley | Any judge fix needs archetype-scale moves |
| C35 R1 | A second seed, then adoption into R1 |
| C30 ok | W becomes Stage 3's bootstrap and C39's P0 |

## 4. Decisions for Evan

1. **Decided 2026-10-22: option (a), training and judging (Evan, row 41: "Sure try using that time limit"; log #161).** T comes from C02 (`reports/C02-round-length/record.md`), else the prior Π. **D1, follow-up to rows 24 and 26.** May an unfinished game at turn T be decided by Prizes as the 2000 event scored
   it (time win 2/3, Prize tie 1/3; pilot seat points +1/+1/3/−1/3/−1)? Options: (a) training and judging, or (a')
   only the judged games that score decks.
   *Evidence:* exact per-turn re-scoring of 576 greedy games puts the walls at 0.48-0.55 of STS points at cuts 20-40
   (0.64-0.66 under #139's proxy). One-turn search on both seats with a 50-60-turn cut gives 0.44-0.46 (#147), while
   the plain draw he chose relapsed at 70 and 120 turns and flattened payoffs at 40.
2. **D2, only if D1 is yes.** How is T fixed: from C02's documented round length, frozen before any run; from the
   game's own self-play length; or drawn per game from a stated prior? It is never set by its effect on distance to the
   lists.
   *Evidence:* the walls' exact greedy share rises monotonically with the cut (0.48 at 20, 0.55 at 40, 0.62 at 50,
   0.67 at 60), so T alone sets the verdict.
3. **D7.** Go-ahead to commit the work since fa32895 (#127).
   *Evidence:* git status shows 27 uncommitted paths (15 modified files, +1,361 lines), and every flag since #128 exists
   only in the working tree.
4. **Engine fixes behind default-off flags:** the `env/game.js` ending-label fix, and #139's verified deviations in the
   ryuu-play submodule (2003 Confusion rule, simultaneous-win draw, Maintenance order, Thick Skinned cure edge).
   *Evidence:* #139 verified each one, and the label calls a no-Pokémon win against an empty deck a deck-out, which
   skews every deck-out statistic and any deck-out-0 reward.
5. **C40: Stage 3 bootstrap components.**
   - (1) A kind-aware base measure for the head's incoming draw. Its 0.8 / 0.2 constants are hand-set and drift toward
     20/20/20.
   - (2) A pilot-first warm-up, and its stop criterion: the ending share, which singles out some endings, or a
     game-agnostic positive Prize margin.
   - (3) `wide_deck` (hand-set constants, median start 8/29/20+2) vs the flat `random_deck` (mean about 20/20/20) for
     start and turnover decks.

   *Evidence:* a uniform incoming draw over this pool is 81% Pokémon and 2% basic Energy (#124), and a plain-result
   pilot fell from 92% to 7% deck-outs by iteration 24 on fixed decks (#71). With no answer in a day, C41 runs as a
   diagnostic at the game-agnostic level.
6. **Pilot-v2 lineage.** May a pilot-v2 descendant (C17's W1, C39's P0, and every current pilot through #69) be a
   method component, or must Stage 3 start from a human-free pilot such as C30's W?
   *Evidence:* pilot-v2's 512 training decks use 52 cards of the human lists' pool, and it was paid 0 for deck-out
   wins, the setting ruled out on 10-09 (#51).
7. **Decided 2026-10-22: approved "for now" (Evan, row 39; log #152).** **The method and its Judge row.** Approve `notes/method.md` (replacing plan-lab and plan-rediscovery, his targets
   kept) and its new Judge scorecard row (JF1-JF4) as a gate before any judge drives selection.
   *Evidence:* co-adapted pilots rate the walls 0.68-0.75 against the lists and pilot-v2 rates them 0.24-0.26 (#137,
   #147), while 25 of 27 screens since #127 tested meta-level fixes under the co-adapted judge.
8. **Retire the lab main line formally** (README Next item 4; `runs/lab/STOP` is already written).
   *Evidence:* the lab has been idle since 10-20 23:05, and a restart would resume the pre-#127 forced-swap recipe and
   rerun card 020, already screened as scr-practice (#129-#133).
9. **Conditional, only if C09 finds R1:** should the opponent's full decklist leave the pilot's inputs in training (a
   change to the game's information sets, C33 D6)?
   *Evidence:* OPP_DECKLIST tokens show the whole opposing list at every decision, which a 2000 player lacked, and
   #73's no-deck screen lost no strength.
10. **Conditional, before any adoption:** rule-3 sign-off for a hand-built meta-level rule that a diagnostic supports:
    islands or a torus (C43), a hard cap (C44), QRE/Nash allocation or lexicase (C27), or C38-B's supertype correction.
    *Evidence:* the method's rule 3 sends any hand-built cap, acceptance rule or niche that is not simpler than what it
    replaces to Evan.

## 5. Outside research (C02's questions, in this order; T's formula is written down before any reading)

1. **STS California 2000 (22 July 2000, Long Beach):**
   - the round length per age division (15+, 11-14, 10 and under);
   - what happened when time was called (stop, finish the turn, extra turns);
   - the points (confirm 3 / 2 / 1 / 0);
   - one game per Swiss round?
   - the number of rounds, the top cut, and how top-cut games at time were decided.
2. **Engine turns per round:** how many engine turns (both players' turns) a 20-minute Base-Jungle-Fossil-Rocket round
   allowed, how often rounds reached time, and what share of games ended by deck-out. Use ≥ 2 independent primary
   sources, one unit (engine turns), and record the division.
3. **Human pace (H-pilot-slow, a separate axis):** how many turns human Haymaker and Wigglytuff took to take six Prizes
   in named matchups (Haymaker mirror, Haymaker vs Wigglytuff), against our pilots' 34-41 engine turns. Prize wins
   only, median and range, noting the selection bias toward quick wins.
4. **2000 procedure rules:**
   - first-turn draw, attack, Trainer and evolution legality;
   - the mulligan extra-card rule;
   - the pre-2003 Confusion rule;
   - simultaneous wins and Sudden Death;
   - exactly when a deck-out loss occurs (Base-Rocket rulebooks, 1999-2000 Compendium).
5. **Stall decks (only after T is recorded):** were Chansey/Snorlax walls with Potion Energy, Full Heal Energy, Energy
   Removal and Gambler, or other stall decks, played from April to November 2000, and how did they fare in rounds where
   time was called? Only time-called records count, and "they were rare" settles nothing.
6. **Phase B and C rules,** fixed before any run: Worlds 2005 (games per match, round length, extra turns, unfinished
   matches) and the Magic Tournament Rules (50 minutes, five extra turns, then a draw; 3/1/0).
7. **Age divisions:** did the three age divisions share rules, and are the 24 lists each division's top 8?
8. **Archives, identification only:** recorded era-format games (TCG ONE, ryuu.eu, Discord leagues) usable for the
   game-length questions. No contact with players and no live evaluation without Evan.

## 6. Declutter now (reversible, no rule change)

1. **Write log #150:**
   - the exact-STS chain: prizeTrace, `sts_points()`, `sts_greedy_all24` 576/576 identical to the stored rows;
   - exact vs proxy at the cuts: 0.482/0.657 at 20, 0.553/0.641 at 40, 0.620/0.655 at 50, 0.665/0.675 at 60;
   - search on the human side 0.536 on the subset; search on both seats 0.647 at 166 of 192, unfinished;
   - the two-turn search final, 0.583 ± 0.099 at 96 games;
   - scr-t60gate479's EPIPE death at 498, on pre-judge-search code with 2 workers, so it was not a concurrent control.

   Then write #151 for this method and plan. `runs/lab/STOP` and README already cite #150.
2. **Install the method and the ledger:** `out/method.md` as `notes/method.md`, and the ledger as `notes/hypotheses.md`
   with this plan's Queue at its head. Both are cited, by README Next and `runs/lab/STOP`, and both are missing.
3. **Stop file:** write `runs/screens/scr-t60gate479/STOP` with its reason; `screen.py list` shows it as live.
4. **Lab index:** write `runs/lab/INDEX.md` mapping each lab card in error, stopped or running (019 ×2, 017 ×2,
   012-deep8, 016-scratch, 009-memgru, 020) to the log entry that settled it. Cards stay untouched.
5. **Screens index:** write `runs/screens/INDEX.md`, giving each folder its candidate, entry and verdict, or "not
   read" (`_killed-2327`, scr-judge, scr-judge-select, scr-resetent10, scr-practice1k, scr-select, scr-draft,
   scr-typecap, and the rest). Index only; nothing moves, so fork paths survive.
6. **Recipes:**
   - write `notes/recipes.md`, with R0 fully resolved and the stacked screen recipes frozen as legacy, each flag with
     its source entry and status;
   - add help strings in `rl/metagame.py` and `rl/train.py` naming the adopted value wherever the argparse default
     differs: swaps 3 vs 6, draft-margin 0.5 vs 0, lr 1e-4 vs 2e-4, draft-lr 1e-3 vs 3e-4, epochs 3 vs 2, shaping 0 vs
     0.1. Defaults stay unchanged.
7. **Copy (not move) analysis scripts** into `notes/scripts/meta_lens/` from the 9afecfab session scratchpad:
   `hodge_audit.py`, plus `meta_lens/{op_audit, lineage, descriptor, boundary, price}.py`. C16, C24, C31 and C44 cite
   them, and temp scratchpads get cleaned.
8. **Banners** on `notes/plan-lab.md` and `notes/plan-rediscovery.md`: "superseded by notes/method.md; targets kept in
   §3".
9. **Evaluators:** mark `runs/probe/after_diag.sh` obsolete, and note one evaluator per question:
   - `probe_matchups.py` for greedy GPU verdicts;
   - `walls_vs_humans.js` for psearch and the STS rule;
   - `gpu_matrix.py` for matrices.
10. **Mark `sts_search_both_sub.jsonl` incomplete (166/192)** in the index, so it is finished (C13), not rerun.
11. **`notes/evan-requests.md`:** set row 37 to tried, with a pointer to this plan and log #151.

## 7. Parked (with reasons; none failed review)

C33 and C40 are not parked. They are portfolio item 4, with their content in §4. C33's D1(a') comes back once C20
reports.

| Id | Why parked |
|---|---|
| C01 | The measurement half is already done (#150 chain: R2 holds, 576/576 replay match). The remaining engine round-rule option, extended trace and opt-in label flag serve only C15, C16's rule cells, C31-B, C34 and C33(a'). Build it (2-3 h) the day one is scheduled or Evan answers D1 |
| C04 | The registry is written by hand this cycle (declutter 6). Launcher enforcement (4-6 h) can wait. A gate-bare null would license only "inert at 479", and the fresh-start check it needs belongs with Stage 3 (C41). Revisit if C29 shows the gate is real |
| C05 | Belongs to the first periodic review (§15). The method's starting horizons are conservative, so no cycle-1 kill depends on it. The cross-pair Spearman needs the SNR-vs-A/A redesign first |
| C06 | Low prior. Its fixes are submodule edits awaiting Evan (§4, item 4). Run the narrowed audit and the paired re-probe of #139's known deviations once he answers |
| C11 | Needs C10's line-scored puzzles and exact prompt scoring (about a day or more). P routing waits for C10's R1/R2 verdict |
| C12 | Needs C03's searched path and a per-decision logger (3-4 h). Cycle 2 if C13 stage 2 or C10 leaves a searched plateau |
| C15 | Needs C01's runner trace, a per-game dump and an offline pick/rloo replica (about 5-7 h). Its fixed-play answer does not gate C34, which waits on Evan |
| C16 | Stage 1 (trimmed panel, hodge_audit port and extensions, half a day to a day) runs in cycle 2 after C07 names the judges. Stage 2 needs C03. This cycle's C07 and C13 cover its walls-vs-lists edges |
| C18 | Subordinate to C07's payoff/exposure split. Needs a held-out-pilot readout and 2 slots. Cycle 2 if C07 points to exposure |
| C19 | Its H1-vs-H2 verdict needs W, which C30 builds this cycle. Cycle 2 with W and the Haymaker-core control |
| C20 | Needs C03's search pass-through and C26's aligned builder (about a day with them). It is C38's gate. Cycle 2 |
| C21 | Needs C16's matrices and C17's independent-network judges. Without them R-collinear holds by construction |
| C22 | About a day of engineering plus 1-1.5 GPU-days. Prior lowered by #134-#138 (the 460-era weights regained about 60 Elo under a varied field) |
| C23 | Its consumer C41 waits on C40's ruling and C30's W. Run in cycle 2, before C41 (4-6 h of agent time) |
| C26 | Shares the aligned builder with C20's (h) arm. Run both in cycle 2, after C03 |
| C27 | Its J1 arm is a positive control (pop829 is a Condorcet winner over the lists), and its consumers (C43, C44, C32) are parked. Run after C16 stage 1 supplies the human-free panel |
| C31 | §7 puts the offline fixed point (C16) first. Wave 1 is about 8 slot-hours plus 2-3 h of scripts, and its R arm is predictable from JF1. Cycle 2 after C16 stage 1 and C30 |
| C32 | 3-4 days of code plus 1-3 GPU-days. Its prerequisites C24, C26 and C16 are unmet |
| C34 | Needs Evan's approval of the round rule in training and of T's source (C33 D1a/D2), plus C01, C10 and C13. The relayed "cheaper spend" message is not that approval |
| C36 | 2-3 days of code. Needs the testbed and C10's line-scored puzzles. Run if C35 and C10 point to competence (R2) |
| C37 | 1.5-2 days. Gated on C03's CRN self-agreement ≥ 0.80, and on C10, C11 and C12 |
| C38 | Gated on C20 (cycle 2) and C03. Arm A is about 15 h of one slot overnight |
| C39 | Needs a P0 (C17's measured F or C30's W) and Evan's ruling on the pilot-v2 lineage (§4, item 6). About a day of code |
| C41 | Needs C40's ruling, C30's W and C23. Cycle 2, or the one-day fallback diagnostic |
| C42 | Depends on C24. Its random-one credit control runs on C24's bench in stage 2 if drift is found |
| C43 | 1-1.5 days. Under J1 the walls are a Condorcet winner, so §7 reads S/X arms only on mechanism readouts, and C27 predicts a null. Wait for C27 and C16 |
| C44 | Gated on C43. Its thresholds need normalising first (diagnosticity 4) |
