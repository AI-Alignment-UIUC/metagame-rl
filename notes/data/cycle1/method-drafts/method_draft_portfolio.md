# The method: how the loop chooses, runs and closes experiments (draft, 2026-10-21)

Every session applies this file; it replaces `notes/plan-lab.md` and `notes/plan-rediscovery.md`. Research runs as a
portfolio: rival accounts of the failure stay side by side, each experiment is bought for its information per
desktop-hour, neglected causal nodes get a floor of effort, and stopping and looking outside follow written rules. In
#128-#147 most screens stacked one flag on the incumbent and moved nothing; three cheap probes (#137, #139, #147) did.

## 1. Goal and ground truth

- **Goal (CLAUDE.md):** from its own play, the agent relearns a drafting style that abstracts its in-game knowledge and
  reaches the human metagame, with nothing human in training; then the same method, unchanged, on Worlds 2005 and Magic.
- **Ground truth, for evaluation and diagnosis only:** the 24 STS 2000 California lists: median 13.5 Pokémon / 28
  Trainers / 18 Energy (ranges 10-18 / 18-34 / 14-25), 8 archetypes (Wigglytuff 10, Haymaker 7), effective number
  3.6. They are optimal (Evan): a consistent deviation (more Energy, fewer Trainers, one type) is a process error.
- **Rules:** self-discovery (no human lists, bots, card-specific moves or game-specific shaping in training);
  game-agnostic (cards, legal options, results and the game's own end score; it must carry to Magic); learned and
  simple at the meta level; Evan's ideas first; the game's definition (a clock, the STS round rule) is his call. Kill
  rules prefer human-free readouts, each candidate counts its reads of the human lists, and nothing reads Worlds 2005.

## 2. Objects and ids

- **`notes/hypotheses.md`, the ledger:** nodes N1-N13; families H01, … (scoped status, tests with their log entries,
  exact do-not-repeat configurations, untested variants H23a, …); facts S01, …; anomalies A1, …; coverage gaps. Ids are
  never reused; a new H id needs a mechanism not yet in the ledger that predicts differently from every family.
- **Accounts**, at the top of the ledger: per open question (Q1, why one wall type takes the population; Q2, why runs
  from scratch collapse into Pokémon piles), at most 8 mutually exclusive accounts W1, …, each a conjunction of H ids
  ("clockless game × prize-race tactics"), plus W0, "none of these", never below 0.1; weights move in steps of 0.05.
  Split an account only when an affordable experiment separates its parts; merge accounts that none separates.
- **`notes/queue.md`, candidates C001, …:** question, W and H ids, node, kind (probe, screen, build, outside round,
  A/A), each live account's predicted band, cost, rate (§4), manipulation check, looks, kill rules and status; closed
  rows keep the observed band and the verdict.
- **`notes/recipes.md`:** R0, the adopted main-line recipe, each flag with its adoption entry; R1, … add components with
  source entry, H id and status (adopted, replicated, single seed, inert, refuted). A launch names a recipe and an
  explicit delta, never argparse defaults (six still hold pre-adoption values).
- **Runs are named by candidate:** `runs/screens/C017-jsearch-s3`, control `C016-ctl-s3`, `runs/probe/C020-audit/`.
  `screen.jsonl` holds candidate, W and H ids, recipe and delta, fork, seed, control, code hash (of the diff),
  predictions, readout, window, looks and kill rules; `runs/screens/INDEX.md` maps folders to candidates and verdicts.
- **Cost, in desktop-hours (dh):** an hour of one of the three screen slots; a CPU probe beside screens costs 0.25 dh an
  hour, a GPU probe 0.5, an agent-hour 1; builds count toward the candidates that need them. A **milestone** is an
  adoption into R0, a settled account (weight ≥ 0.8 or ≤ 0.05) or a scorecard row changing status.

## 3. Scorecard and node-matched readouts

The scorecard is the ground truth, read at each screen's end and each milestone. A candidate is decided on the readout
of the node it targets, against the noise shown; deck-shape trajectories decide drafting and selection candidates only.

| Scorecard | Readout | Noise (A/A) | Target |
|---|---|---|---|
| Shape | top-12 distance (L1 to 13.5/28/18); median P/T/E | window mean RMS 2.0-4.8; one iteration SD ~1.9; medians 1.3/1.4/0.8 | ≤ 6; medians in the human ranges |
| Types | core-card share; effective number of types (game-agnostic clusters); card distance of the best decks to the nearest human archetype | to measure; largest type matched within ~15 decks in A/A | in the 24 lists' band; ≥ 3 types; ≥ 3 human archetypes approached |
| Matchups | best decks vs the 24 lists, under a judge that passes fidelity | SE 0.013 at 1,152 games | ≥ 0.5; incumbent type < 0.5 |
| Robust | every row on 2 seeds, 20+ iterations after the fork and 10+ past the best; then from random decks and a fresh pilot | — | holds |

| Node | Readout that decides it | Noise or bar | Minimum horizon |
|---|---|---|---|
| N1 game definition | ending mix; capped and time-draw share; incumbent vs the lists under the matched end rule | deck-out share RMS 0.08 | 5 it. endings, 20 decks |
| N2 tactics, N3 generality, N11 architecture | puzzles by class; Trainer-value panel; Elo vs a reference pilot (pilot-v2 for N3) on fixed panels and deals | competence RMS 0.025, bar 0.06; Elo σ 8.8, bar max(15, 2σ) | 20-30 it. |
| N4 judge | JF1 incumbent vs the 24 lists; JF2 the judge's logit equilibrium on the 24×24 matrix vs the field's shares (TV); JF3 the N2 readouts under the judge; JF4 empirical-game audit: is the incumbent a Condorcet winner or the only sink on resolved edges | JF1 SE 0.013; JF2 not by Nash LP at 32 games a pair | probe; in the loop flips from 3 it., types from 20 |
| N5 selection | moves vs the A/A null (gate ~15%, ungated ~73%); flips vs the redraw null; accepted moves that hold on fresh paired games | binomial | 3 it. rates, 20 decks |
| N6 draft operator | kinds proposed vs accepted, in and out; h_in, h_out | h_in RMS 0.38; moves RMS 5.7 | 10 it. |
| N7 ecosystem | core-card share; effective types; support of the population's type-level matrix | as Types | 15-20 it. |
| N9 bootstrap | prize vs deck-out endings, attacks, Pokémon count, from scratch | to measure (collapse: 85-99% deck-outs) | 40 it. |
| N8, N10, N13 | score at birth vs after equal pilot adaptation; credit by decisions to the end, value EV; proxy-vs-games rank correlation | to measure | probes |

Bands come from two forks at 160 and one pair at 479, so three reseeded A/A screens of the current base (N12) come
before reading any screen difference under 2 RMS. JF pass values (at least JF1 < 0.5) go into the ledger before use.

## 4. The portfolio

**Information per desktop-hour.** Before launch, each live account (weight ≥ 0.05) predicts a band of the primary
readout: 2-4 bands, each wider than 2 noise SDs, predicted softly (0.7 on its band, 0.3 shared by the others; W0
uniform). EIG = entropy(B) − Σ w·entropy(B | W) is the mutual information in bits between band B and the accounts; the
**rate** is EIG per dh (`notes/scripts/eig.py`, to build, computes both from the queue).
- A screen needs two accounts of weight ≥ 0.1 that predict different bands. Example (3 bands): W1 0.5 and W2 0.4 on
  opposite bands, W0 0.1, give 0.26 bits, so 0.26 bits/dh for a 1-dh probe and 0.044 for two 3-hour screen seeds; when
  all but W0 predict alike ("relapses like the control"), the same screen gives 0.006.
- Floor: 0.02 bits/dh (a starting value). A slot that no candidate clears runs an A/A or a replication seed, or stays
  empty; it never runs a new flag on the incumbent.
- Weights start from the ledger's evidence; then only results (w ← w·P(observed band | W), renormalised) and outside
  rounds move them. If 2 of the last 3 results fell in bands no live account predicted, the accounts are misspecified:
  suspend the ranking and fire O3 (§9).

**Act, test or drop** (Pauker and Kassirer). For a pending decision (adopt into R0, build, ask Evan to change the game,
end a line of work): p = the weight of the accounts under which acting is right, C = the cost of the cheapest test that
settles it, L_wrong and L_miss = the costs of a wrong act and of a missed one (dh). Act if p ≥ 1 − C/L_wrong,
drop the tests if p ≤ C/L_miss, test in between; for adoption into R0 (L_wrong ~30, L_miss ~20, test ~3), act at 0.9 and
drop at 0.15. A cheap, reversible change that is right under every account (a measurement, a bug fix) needs no screen.

**Allocation**, in order: Evan's ideas; running candidates to their horizon; probes by rate in the CPU and spare-GPU
pool; screen slots by rate. A probe that tests a screen's premise for under a fifth of its cost runs first. Screens
launch in batches: one control and up to two arms on the same fork, recipe, code hash and `--reseed`.

**Exploration floor**, over the last 10 launched candidates:
- at least 3 on nodes other than the two the top accounts sit on, and 1 on an under-tested node (now N8, N9, N13, and
  N1's payoff for unfinished games); no node above 60% of the slot-hours in any 24 hours;
- every account of weight ≥ 0.05 with a distinct untested variant tested within 20 candidates, or a written deferral;
- at least 1 in 4 screens on a cause starting before the incumbent type formed (wide decks under a pilot not grown in
  the population, or from scratch), so that prevention is tested and not only escape;
- at each milestone, a coverage pass: every node's families and gaps listed, each gap given a stub H row.

## 5. The cycle

A cycle starts on a result, a free slot, a message from Evan or a loop tick, and ends when a candidate closes.
1. **Ingest** new looks and outputs: each readout with its noise band and its likelihood under each account.
2. **Record** the log entry from the outputs, then the ledger (tests, scoped verdict, weights, facts) and the queue.
3. **Check** the outside triggers (§9) and the floors (§4).
4. **Propose** from untested variants, anomalies, coverage gaps, outside rounds and Evan; apply §6 and the rules of §1.
5. **Price:** bands, manipulation check, cost and rate; mark each pending decision act, test or drop.
6. **Allocate** (§4): at most 3 screens, CPU diagnostics alongside, and the 80% caps of CLAUDE.md.
7. **Pre-register** in `screen.jsonl` or the probe's header, then launch.
8. **Monitor** at the looks (§8) and kill then and there.
9. **Close:** verdict into the queue and the H row; README Next rebuilt from the queue; evan-requests.md for Evan's.

## 6. Distinctness and stacking

- **Distinctness.** Key each candidate by node, lever, H id, direction, dose, judge, fork, horizon and seeds; list the 3
  nearest past tests (grep the H ids and the log). It passes only if it (a) tests a family with no test, (b) changes a
  dose, condition or confound its H row lists as untested, or (c) a live account of weight ≥ 0.1 predicts a different
  band for it than the nearest past test's observed outcome. If all accounts predict it from a past result, it repeats.
- Do-not-repeat entries bind unless the candidate names the confound or dose it removes; too-broad entries are narrowed.
- **Stacking.** An arm is a recipe plus at most one untested component. A recipe is a base only if every component is
  adopted or replicated on 2 seeds, and at most two levels above R0 without a replicated result. A component with no
  effect beyond A/A in an ablation or factorial leaves the recipe (Occam).
- **Interactions** predicted between levers are tested as a 2×2, as probes where possible: turn limits (#143) and
  one-turn search (#146) each failed alone, and together put the walls at 0.44-0.46 (#147).

## 7. Experiment design

- **Upstream first, by oracle swap:** replace a link with an oracle or near-oracle (the round rule for the game, search
  on both seats for the judge, seeded archetypes for exploration, diagnostic only) and watch the downstream readout.
  N5-N7 candidates enter the coupled loop only under a judge that passes fidelity, else a surrogate metagame (fixed
  payoffs with known equilibria, injected judge bias, binomial noise): under a biased judge all accounts predict a null.
- **Manipulation check:** what the treatment must change, by how much, by iteration 3 (searched games flip selections
  beyond the redraw null; a limit binds in a stated share of games). Dry-run a new selection rule on logged games first:
  `scr-jsearch479` would have failed (6 flips in 18 iterations against 15.5 from noise, #149).
- **Matched control:** concurrent, same fork, recipe, code hash, workers and `--reseed` (unlike `scr-t60gate479`, #148).
- **Seeds:** one seed is exploratory and can only promote a candidate to replication; a claim, an adoption or a stacking
  base needs 2 or more. Probes use identical deals, and paired candidate-incumbent games where the code allows.
- **One evaluator per question,** named in the candidate (`probe_matchups.py` greedy, `walls_vs_humans.js` search).
- **Verdict scope:** "refuted" needs a passed manipulation check, the minimum horizon, 2 seeds or a powered probe,
  and for N5-N7 a judge that passes fidelity; otherwise "not supported as tested", with dose, horizon, judge, fork and
  seeds. Verification overturned 7 of the ledger's 29 refutations.

## 8. Monitoring and kill rules

- **Probes:** a betting confidence sequence on the mean or the paired difference (`notes/scripts/anytime.py`, to build),
  valid at every peek; stop a pair or contrast once it excludes the decision value ± 0.05, or at its game cap.
- **Screens:** the run is the unit, as iterations are autocorrelated. Looks at 3, 5, 10, 15, 20 and 30 iterations after
  the fork can only stop a run; claims come from seeds.
- **Evidence over seeds, anytime-valid:** per seed, D = arm minus control on the pre-declared window mean, s = the A/A
  RMS of that difference (its upper end until three A/A runs exist), δ = the middle of the predicted effect band;
  LR = exp((δD − δ²/2)/s²), multiplied over seeds. At 10 or more the effect is supported, at 0.1 or less not supported
  at this dose; in between, add a seed only if its rate beats the queue, else close as unresolved with the LR.
- **Stop then and there** (Evan's rule) on any of:
  - manipulation check failed by iteration 3: "untestable as built"; fix or drop;
  - harm: worse than the control by more than 2 RMS at two looks in a row;
  - futility: within 1 RMS of the control at two looks in a row past the minimum horizon, against its prediction;
  - machine failure (sleep, shutdown, memory): "killed by machine", not a verdict; relaunch or close it explicitly.
- **No success** on one seed, nor before 10 iterations past the arm's best and past its control's relapse window (10-16
  iterations after a fork from a wall state, S03). Minimum horizons are provisional: set each where the readout's
  early-vs-final rank correlation over past screens reaches 0.7, and recompute every 10 closed screens.

## 9. Going outside the system (Evan, rows 32-33)

Outside means literature and theory, the game's real-world context, or a question to Evan. A round runs beside the
screens (no slot), costs 1-3 agent-hours, starts from a brief (the accounts and weights, the anomalies, the relevant H
rows, one sharp question) and must return families with predicted bands that pass §6. One trigger starts a round:
- **O1 stall:** none of the last 5 closed internal results changed the odds between two accounts of weight ≥ 0.1 by a
  factor of 3, or together they moved the weights by under 0.25 bits (summed KL divergence, posterior to prior).
- **O2 exhaustion:** no queued candidate clears 0.02 bits/dh; or the bottleneck node has no untested variant predicted
  to move its readout by 2 noise SDs; or W0 reaches 0.3; or every named account has failed a prediction.
- **O3 anomaly:** a result in a band no live account predicted that reproduces once; or §4's calibration rule; or an
  anomaly (A1, …) still unexplained after one targeted internal check.
- **O4 repetition:** 2 of the last 5 proposals were near-duplicates, or one mechanism has 3 not-supported variants.
- **O5 capability gap:** the top candidate needs an unbuilt technique whose design choices matter (soft gated search
  targets, imperfect-information search, sequential tests): targeted how-to research before building it.
- **O6 premise:** a decision hinges on a fact about the real game or the ground truth that no run can produce: research
  the domain and bring Evan the evidence (fires now: turns in a 20-minute STS round, how stall decks fared; H03, H04).
- **O7 dead end:** the audit JF4 finds the incumbent type a resolved Condorcet winner or the only sink against the human
  archetypes under every affordable judge: stop meta-level screens; the levers left are a stronger judge or the rules.
- **Floor:** one round per 10 cycles or per milestone, whichever comes first.

Do not go outside while a cheap, discriminating, untested internal candidate with written predictions waits and no
trigger has fired: run it. Score a round by its families' first two tests (new to the ledger, odds moved by 3 or more);
after two dry triggered rounds in a row require two triggers (O3, O6, O7 still act alone); after three, only the floor.

## 10. Evan's ideas first

- A new idea from Evan enters `notes/evan-requests.md` and the top of the queue the same turn and is tried fully (its
  strongest version plus a variant) ahead of the ranking, still with predictions and a manipulation check. If it repeats
  a tested mechanism, tell him which test covered it and run its untested form unless he says otherwise.
- When he states a cause (the computer was off), accept it. Game-definition changes and commits wait for him.

## 11. Logging

- One progress-log entry per closed candidate, outside round or declutter step (CLAUDE.md's format, from the run's
  outputs): the title names the candidate id; Evidence, readouts with noise bands and the LR; Found, the H and W ids
  that moved (weights before -> after) and any trigger fired; Next, candidate ids. Ledger and queue follow the entry.
- README **Next** is the queue's top 3-6 in allocation order, with candidate ids, rebuilt every time.

## 12. Decluttering

- One home per fact: the log (history), the ledger (mechanisms, accounts, facts), the queue (candidates), `recipes.md`
  (flags), this file (rules). Old plans get a "superseded by notes/method.md" banner; nothing is deleted.
- No launch with log debt: every finished result is logged first (at adoption: the two-turn search at 96 games).
- Every run folder has an end state (finished, STOP with a reason, killed by machine) and an INDEX.md row; index, don't
  move (forks read `population_it0479.pt`, `seg_0460.pt`). An index closes the retired lab's 'running'/'error' cards.
- `screen.py` launches from a recipe id; a flag whose default differs from R0 says so in its help string.
- Memory notes, README lines and plans the ledger contradicts are fixed in the same cycle; at milestones, ask Evan to
  commit. Decisions use game-agnostic readouts (core-card share), not card-name counts; names stay in diagnosis.

## 13. Session-start checklist

1. Read `Desktop/333/CLAUDE.md`, the repo's `CLAUDE.md`, `MEMORY.md`, this file, the accounts, the queue, README status,
   the last 3 log entries and new rows of `notes/evan-requests.md`.
2. Check the machine (`nvidia-smi`, free RAM, processes) and each screen's last iteration and STOP state.
3. Clear log debt; give every dead run its end state (machine deaths are not verdicts).
4. Give each new message from Evan a row, and each idea the top of the queue.
5. Apply the looks and kill rules to running screens; check O1-O7 and the floors.
6. Refresh the rates, fill free slots and the probe pool, and make README Next match the queue.
