# Method: how the loop picks, runs and records experiments (2026-10-21)

Applied every session; it replaces `notes/plan-lab.md` and `notes/plan-rediscovery.md` (kept, marked superseded). The
research loop failed the way the model did (log #120-#147): it forked two wall states, stacked flags on the incumbent
recipe, read a noisy short-horizon score and kept no archive, so 19 of 27 screens reused a recipe and six mechanism
families came back in 3-6 forms each. So the research gets the model's remedies: an archive with niches and
near-duplicate rejection, lineages that do not share flags, resets, decisions above noise, triggers for looking outside.

## 1. Goal and ground truth
- **Goal.** From random decks and a fresh pilot, with nothing human in training, draft and play a metagame that
  matches the 2000 STS field; then, with the method unchanged, Worlds 2005 (held out) and Magic.
- **Ground truth, for evaluation and diagnosis only:** the 24 STS 2000 California lists, median 13.5 Pokémon / 28
  Trainers / 18 Energy (ranges 10-18 / 18-34 / 14-25), 8 archetypes (Wigglytuff 10, Haymaker 7, Sponge 2, five
  singletons), effective number 3.6. Evan: they are optimal, so a consistent deviation (more Energy, fewer Trainers,
  one type) means part of the process is wrong. They may score, diagnose and seed diagnostic arms (fixed-point or
  invasion tests), never train or choose a method component. Worlds 2005 stays sealed.
- **Evan's rules.** (1) Self-discovery: no human lists, bots, card-specific moves or game-specific shaping in training
  (pilot-v2's deck-out-0 reward is shaping: flag it wherever it anchors or judges). (2) Game-agnostic: cards as
  features and text, legal options, results and the game's own end score; it must carry to MTG. (3) Learned and
  simple: one draft policy learned from real results, reading decks through the pilot. (4) His ideas first.

## 2. Scorecard and readouts
The scorecard measures distance to the ground truth; a node's readout decides experiments on that node (deck shape
cannot judge a pilot change in 10-20 iterations). A difference counts above 2x the band in both seeds, or 3 SE for a
probe. Bands are provisional until the first internal job, an A/A of the base recipe R0 (section 5) on 3 reseeds.

| Row (ground truth) | Readout | Target | Band now |
|---|---|---|---|
| G1 Shape | top-12 mean L1 to 13.5/28/18, 3-iteration smoothed; median P/T/E | ≤ 5; Energy 14-25 | A/A RMS 2.0-4.8; medians 1.3/1.4/0.8 |
| G2 Cards | staples a top deck (lists 8.5 of 10); card distance to the nearest list | ≥ 7 staples | not calibrated |
| G3 Types | human archetypes present (overlap ≥ 0.5); effective number of types; largest type | ≥ 3; about 3.6 | A/A up to 14 decks |
| G4 Verdict | best decks vs the 24 lists: greedy population pilot, one-turn search on both seats, each also scored under the STS round rule | about 0.5, not above | SE 0.013 at 1,152 games |
| G5 Endings | deck-out and prize shares, turns a game, vs human-list games under the same judge (deck-outs 27-35%) | that baseline | deck-out RMS 0.08 |

G1 and G3 are necessary, not sufficient (#114, #140). G3 needs a card clustering calibrated to the lists' 8 archetypes;
until then also count decks holding the two commonest non-staple cards (now Chansey and Snorlax, 73-80 of 99).

| Nodes | Component readout (one evaluator each) | Band now |
|---|---|---|
| N1 game | ending mix; turns and decisions a game; share ended at a cap or limit; pass and attack rates per side | deck-out RMS 0.08 |
| N2, N3, N10, N11 pilot | s1 (puzzles, Trainer-value panel); Elo vs pilot-v2 and the base pilot on fixed panels; value variance by decisions to the end; credit probe | s1 bar 0.06; Elo σ 8.8 |
| N4 judge | JF1 walls vs lists; JF2 its equilibrium on the 24x24 lists vs the field's shares; JF3 s1 under its play; in the loop, selection flips vs the redraw null | SE 0.013; flips above 2x null |
| N5-N7 selection, draft, population | decks moved vs the null (~74 of 99 ungated); Energy and Trainer change of accepted vs proposed moves; h_in, h_out; proposals by kind; G3; matchup effective rank | moved RMS 5.7; h_in 0.38 |
| N8, N9, N12, N13 | from scratch: prize endings, deck-outs, Pokémon count; gain from practice before judging; A/A spreads; early-vs-final and proxy-vs-real rank ρ | none yet |

Flagged until fixed: #139's deck-out label; pre-turnover type rows; s1 at history 0; two walls evaluators 0.02 apart.

## 3. Objects
- **Ledger, `notes/hypotheses.md`.** Head: the live matrix (rival explanations of the current failure: game length E,
  prize-race play P, judge co-adaptation J, selection and drafting S, an exploration valley X, pilot-v2's verdict as an
  artifact of its reward, the conjunction E x P, catch-all H0), standing facts S01-S30, anomalies A1-A9, coverage table,
  queue. Body: one row per family (H01-H69, new from H70): name, nodes, lever, origin (internal, Evan, outside),
  mechanism, prediction, tests (entry, configuration, result, grade), status, do-not-repeat, variants, rejections.
- **Candidate `H23.2`** (variant 2 of H23). Its card: cell and descriptor; the 3 nearest recorded tests and the
  difference; a predicted band per live explanation; readout, window, decision and kill rules; power check; cost;
  recipe and treatment; rules 1-3 and the carry-over to MTG.
- **Recipes and runs.** Recipes are named, versioned flag sets in `notes/recipes.md`. Runs are named by candidate,
  start and seed: `runs/screens/h23.2-479-s1`, controls `ctl-R0-479-s1`, A/A `aa-R0-479-s3`, probes
  `runs/probe/h23.2/`; `screen.jsonl` holds candidate, recipe version, treatment, bands and rules. Old `scr-*` folders
  keep their names, indexed. A **cycle** ends when one experiment (screen, probe, analysis, outside round) is recorded.

## 4. The archive
The ledger is a quality-diversity archive (MAP-Elites style) over node x mechanism: each family is a cell, its tests
are the cell's members, its most adequate test is the cell's elite.
- **Grades.** A: powered (predicted effect above 2x the band; 2 seeds per arm and control, or a probe with a stated SE;
  the node's minimum horizon; manipulation check passed; no named confound). B: one seed or one named confound. C:
  underpowered, stopped early, killed by the machine or untestable by design.
- **Status follows grade.** Only A tests establish or refute, and a refutation names its configuration ("refuted for
  --draft-ent 0.05 on a reset head from 460"); B supports or weakens; C leaves a family inconclusive, counted as
  untested. Verification corrected 50 of 69 statuses, so each milestone re-checks the statuses changed since the last.
- **Two routes in.** A candidate is queued only if it opens a cell (a mechanism the ledger lacks: a new H id) or would
  become its cell's elite by fixing a named inadequacy of the current one: power, seeds, horizon, a confound, start
  state, judge, or a dose at least 2x outside the tested range.
- **Near-duplicates are rejected:** same cell, lever, direction, dose range, start-state class and judge as a recorded
  test, no inadequacy fixed. A new name, hypothesis string or "X's flags plus Y" is no difference. Before launch, print
  the 3 nearest tests by descriptor (node, lever, direction, dose, start, judge, horizon), grep the log, notes and
  commits for what the ledger lacks, and write the difference into the card. Rejections are dated under the family.
- **Conjunctions** are families of their own (search and a 50-60 turn draw failed alone, worked together offline, #147).
- **Coverage table:** nodes x levers (game rule, pilot data, objective, inputs, search, judge, selection, proposals,
  population, coupling, start, measurement), counting A, B and C tests; empty or C-only cells are coverage gaps.
- **Do-not-repeat** entries name exact configurations (flags, dose, start, judge, horizon), never a whole mechanism
  ("learned change rate" blocked an untested --select variant).

## 5. Recipes, islands and resets
- **Registry, `notes/recipes.md`.** Each component: flags, H id, source entry, status (adopted on evidence, carried
  unverified, inert, refuted). `R0` is the lab's adopted recipe (lr 2e-4, 2 PPO epochs, 6 changes a draw, result-only
  draft reward, draft lr 3e-4, fading shaping 0.1, deck-free pilot) moving decks by the significance gate
  (`--select --candidates 1 --select-z 1`, the one screen-era change beyond A/A, #140), provisional until replicated
  on 2 seeds. The lab's forced moves (#127's ratchet) and the stacked screen recipes (resetcap, ctl479, gate479,
  t60gate479, jsearch479) stay as named legacy recipes for finishing matched comparisons, with no new treatments.
- **Launch.** `screen.py` takes a candidate id, a recipe and one treatment or a factorial design, and refuses a launch
  without a recipe or with a repeated flag (`scr-gate479` passed `--turnover-every` twice). Code defaults equal R0, or
  every run goes through the registry (six argparse defaults differ from the adopted values).
- **Stacking cap:** at most 2 unadopted components above R0. A component joins R0 only on a logged A-grade pass on its
  node's readout; each adoption makes a new version (R1, ...), and matched comparisons hold within a version.
- **Islands.** Four lineages from R0: J, judge and game definition (N1, N4); D, drafting, selection and population
  (N5-N7, N13); P, pilot (N2, N3, N10, N11); S, start and coupling (N8, N9). An island uses another's unadopted
  components only inside a factorial; adoption into R0 is the only migration. They share the 3 screen slots, at most 2
  each; CPU probes and measurement (N12, first whenever a band is missing) sit outside the quota.
- **Resets.** Every 12 experiments, the island with the least movement over its last 4 (results that excluded or
  shifted a live explanation, or moved a status a grade) is reset: its queue is parked, and it restarts from a coverage
  gap or the latest outside round on a start state it has not used, never seeded by the survivors.
- **Start states.** Runs are labelled escape (forked from a wall state) or prevention (from scratch or wide decks). In
  any 10 cycles at most half the screens fork one state, and a quarter are prevention starts (25 of 27 forked 460/479).

## 6. The cycle
1. Record what finished (log debt to zero, section 11) and update the ledger from the new entries only.
2. Check the triggers and floors (section 9); an outside round runs beside the slots.
3. Name the bottleneck: the most upstream link (game definition -> pilot -> judge -> selection and drafting ->
   exploration) whose readout misses its target; now game length and prize-race play, which the judge inherits (#147).
4. Gather candidates (Evan's requests, the bottleneck's untested variants, coverage gaps, outside output); write cards.
5. Check distinctness (section 4). Keep crucial experiments, where two live explanations predict bands that do not
   overlap within the noise, and floor candidates, labelled exploratory. Drop the rest.
6. Rank: Evan's first; the cheapest decisive (probe before screen, testbed before system); floors; exclusions per hour.
7. Launch by id from a registry recipe beside a concurrent control; watch and stop on the node's readout (sections 7-8).
8. Read against the written bands: exclusion, shift, null within noise, untestable, or anomaly (outside every band: R2).
9. Write the log entry, ledger rows, README Recent and Next and the evan-requests row; close what the result touched.

## 7. Experiment design
- **Probe before screen, testbed before system.** A fixed-checkpoint evaluation on recorded deals (minutes on the GPU,
  hours on the CPU) goes first when it can decide; the results that moved the explanation were such probes (#137, #139,
  #147). Each component meets its testbed first: a pilot change the puzzles, panels and head-to-heads; a judge JF1-JF3;
  a meta algorithm a surrogate metagame (fixed payoffs with known multi-archetype equilibria, injected judge bias,
  binomial noise) that runs in seconds.
- **Oracle swaps, delta debugging, factorials.** Swap one link for an oracle (a game rule, a searching judge, seeded
  archetypes; diagnostic only) and watch the downstream readout; between a passing and a failing configuration (pilot-v2
  rates the walls 0.26, population pilots 0.68-0.75) halve the differences; test joint levers as factorials.
- **Controls** are concurrent: same code version, workers, start and recipe version, launched together. A control that
  died or ran on other code (`scr-t60gate479`) is not one. Anything built on (an adoption, a refutation) needs grade A.
- **Power and manipulation checks.** Before launch, the predicted effect must exceed 2x the band at the planned games
  and iterations; within 2 iterations the treatment's intermediate variable must move beyond its null.
  `scr-jsearch479` failed both (about 2 searched games a candidate; 6 selection flips in 18 iterations against 15.4
  from redraw noise): untestable by design, not a refutation.
- **The answer key** steers as little as it can: human-free kill readouts where the node allows; entries count its uses.

## 8. Kill rules
- **Any run, any time:** a machine fault (rerun, no verdict); a failed manipulation check (status unchanged, fix the
  design); clearly worse than control, beyond 2x the band on the node's readout, for 3 smoothed iterations.
- **Drafting, selection and population screens, and judge or game-rule screens past their manipulation check,** run
  at least 10 iterations, then stop as stalled when no readout has left the control's band, or when the arm relapses
  (smoothed distance above its minimum + 5 for 5 iterations, or the largest type past 50). A promising arm runs 15
  iterations past its best before it is called (ungated 479 forks relapsed on distance 4-9 iterations after a minimum).
- **Pilot changes** are never stopped on deck shape: 2 segments of 10 iterations unless clearly worse (Elo below about
  -18, s1 down 0.06), decided on s1 and Elo at the written horizon; non-identity changes are warm-started (#98).
- **From scratch:** stop if prize endings are under 10% at iteration 30 (a plain-result pilot on fixed random decks cut
  deck-outs from 92% to 7% by iteration 24, #71). **Probes** stop at their SE target, or when no outcome could change
  the pending decision.
- Evan's rule (stop what is not making progress, then and there) applies after the minimum horizon. The early-vs-final
  calibration resets each horizon to the iteration where early and final ranks agree at ρ 0.7.

## 9. Looking outside, and the exploration floor
Outside research (literature, theory, the game's history, Evan) opens when any trigger fires:
- **R1 Exhaustion:** the bottleneck has no admissible candidate above 2x its band, or every live explanation has failed.
- **R2 Anomaly:** a result outside every live band, or against a standing fact, unexplained after 2 cycles.
- **R3 Stall:** 3 screens read in a row with no scorecard row beyond its band, or 3 graded nulls (A or B) in one cell.
- **R4 Repetition:** 2 of the last 5 proposals rejected as near-duplicates.
- **R5 Capability gap:** the top candidate needs an unbuilt technique whose design choices matter (how-to research).
- **R6 Premise:** evidence questions the environment or the ground truth (now: turns in a 20-minute STS round, and
  whether stall decks were viable in 2000). Anything that would change the game goes to Evan.
- **Periodic:** a broad sweep every 10 cycles or at each milestone, whatever the triggers say.

Not when a cheap, discriminating, untested experiment with written predictions is available: run it first (R2 and R6
research in parallel). A round's brief comes from the ledger (live matrix, anomalies, coverage gaps, do-not-repeat
lists, sources already read in `reports/` and `research_notes/`); it returns ledger rows with sources, not a report,
and is scored by the admissible, diagnostic candidates it adds. After 2 empty triggered rounds, require two triggers.

**Exploration floor.** A quarter of the desktop-hours of any 10 cycles goes to coverage gaps off the bottleneck (now
N8, N9, N13, the STS payoff, the cut choice, the opponents decks are scored against, prompt decisions, the Energy-count
input, open decklists): 63% of the 214 recorded tests sit on six nodes, while N8, N9 and N13 have 6, 7 and 12.

## 10. Evan's ideas first
- Each message gets a row in `notes/evan-requests.md` the same turn, with its cell and candidate id. His ideas go first,
  ahead of quotas and floors, tried fully: the strongest version plus a variant, at the horizon their node needs.
- The distinctness check still runs: if an idea matches a recorded test, tell him what ran and run the distinct
  variant closest to his intent, or the exact repeat if he asks. A change to the game's definition (the STS round rule
  in training) goes to him with evidence, never adopted silently. When he states a cause, take it.

## 11. Logging and the README
- **Log, CLAUDE.md format.** The plan-item field carries the candidate (`### #151 · 2026-10-22 · A5 H23.2 · <todo>`);
  one entry per experiment read, build, probe, outside round or declutter. **Found** opens with the ledger change
  (`Ledger: H23 inconclusive -> supported (B); H23.5 added`); **Next** names candidate ids.
- **The ledger** changes in the same turn, from the entry, never from memory; a status moves only with an entry that
  cites the evidence. It indexes the log by mechanism, is not a summary level, and adds no claim the log lacks.
- **Log debt:** no experiment starts while a finished run, probe or build is unlogged; no file cites an unwritten entry.
- **README:** CLAUDE.md's recursive rules stand. Where things stand names the bottleneck and the scorecard; Next is the
  top 3-6 queue candidates in order (id and one line), rebuilt each time, never an item the ledger marks tested.

## 12. Decluttering
- **One home per fact, closed where it tempts.** Statuses live in the ledger; plans, memory notes, lab cards, run
  folders and code help strings cite the H id. When a family or candidate closes, mark every place a reader would find
  it open: lab card, run folder, plan, memory note, evan-requests row, README Next.
- **Index, do not move.** Files a fork or resume needs (`runs/lab/main/seg_0460.pt`,
  `runs/screens/scr-resetcap/population_it0479.pt`) stay put; `runs/screens/INDEX.md` maps every folder to its
  candidate, entry and verdict, or "not read". Deleting run data needs Evan.
- **Stop dead machinery** with a STOP file, so nothing resumes a retired recipe; keep **one evaluator per question**,
  named in the readout tables. **Superseded notes** get a banner pointing here; **memory notes** are corrected
  when they contradict the ledger; **uncommitted work** is listed each session and committed only with Evan's go-ahead.

**First pass, before the next screen.** Log the debt: the judge-search build (cited as #148, not in the log),
`scr-jsearch479` stopped at 497 as untestable, `scr-t60gate479` dead at 498 (not a concurrent control), the two-turn
search at 96 games (0.583 ± 0.099), JF2, the ledger and this method. Write `runs/lab/STOP` and an index mapping each
lab card in error to the entries that tested its idea, or "never decided". Build `notes/hypotheses.md` and
`notes/recipes.md`; make `screen.py` require a candidate and a recipe; mark the six argparse defaults. Banner the two
old plans; correct evan-requests rows 12, 24-25 and 32 and the memory notes (human shape 13.5/28/18, the league
refuted, moves by selection, screens rather than lab cards). Ask Evan about committing everything since fa32895.

## 13. Session start
1. Read the two CLAUDE.md files, MEMORY.md, this method, the ledger's head, the README status, the last 3 log entries
   and new evan-requests rows; add Evan's new messages as rows, map them to cells, put them first.
2. Check the machine (`screen.py list`, `nvidia-smi`, RAM; ≤ 3 screens, ~80%); sleep or shutdown kills are faults.
3. Clear the log debt, then sync the ledger.
4. Check R1-R6, the periodic sweep, the floors and the island reset count.
5. Fill free slots from the queue, each launch with its card, recipe, control and seeds; CPU probes alongside.
6. Look for clutter (nothing resumable by accident, registry and defaults in step, no dangling citations), and tell
   Evan about uncommitted work and the decisions that need him.

## 14. Checking the method
The method is a family in the ledger (N12): over the next 12 experiments it should test at least 3 families new to
the ledger, keep near-duplicates under 20% of proposals and beat the exclusions per desktop-day of #128-#147 (about 3
in 25 runs). If the islands do not, drop them and keep the archive check. All numbers here are starting values.
