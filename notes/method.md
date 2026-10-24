# Method: how the loop picks, runs and records experiments (2026-10-21)

**Status:** approved by Evan "for now", 2026-10-22 (`notes/evan-requests.md` row 39, log #152), the Judge row of §3
with it; it stands until he revises it or the §15 check says otherwise.

Applied every session; replaces `notes/plan-lab.md` and `notes/plan-rediscovery.md` (kept with a banner; its approved
targets stay in §3). In #120-#149 the research loop failed like the model: 25 of 27 screens forked two wall states, 19
reused a recipe, and flags stacked on the incumbent were read on a noisy deck score, so "relapses like the control",
predicted by every explanation, excluded nothing; the probes that split explanations did (#137, #139, #147). Hence
rivals side by side, runs able to exclude one, readouts matched to the link, near-duplicate rejection, written rules.

## 1. Session start
1. Read this file, the head of `notes/hypotheses.md` (rivals, Matrix, coverage, Queue), README status, the last 3 log
   entries and new rows of `notes/evan-requests.md`; give each new message from Evan its row now (§11).
2. Machine: `screen.py list`, `nvidia-smi`, free RAM; at most 3 screens, about 80% of the machine, no orphan processes,
   nothing resumable by accident; a run that died in a sleep or shutdown is "killed by machine" (take Evan's cause).
3. Clear log debt (§13); apply each live run's looks and kill rule, stopping what fails them then and there (§9).
4. Score new results (§4-§6); check the triggers (§12), the floor (§8) and whether a periodic review is due (§15).
5. Fill free slots in the order of §6, each with record, registry recipe and concurrent control; CPU probes beside.
6. Before stopping: log, `hypotheses.md`, README Next and `evan-requests.md` agree; list uncommitted work for Evan.

## 2. Goal, ground truth and rules
- **Goal:** from random decks and a fresh pilot, nothing human in training, draft and play a metagame matching the 2000
  STS field; then, with the method unchanged, Worlds 2005 (sealed) and Magic. Rules and readouts name no cards.
- **Ground truth:** the 24 STS 2000 California lists, median 13.5 Pokémon / 28 Trainers / 18 Energy (ranges 10-18 /
  18-34 / 14-25), 8 archetypes (Wigglytuff 10, Haymaker 7, Sponge 2, five singletons), effective number 3.6. They are
  optimal (Evan): a consistent deviation (more Energy, fewer Trainers, one type) means part of the process is wrong.
- **Use of the lists:** scoring, diagnosis, judge tests, diagnostic seeds and keep-or-drop calls on components, each
  counted in its entry; never training data or opponents of a run that feeds the method, a recipe part or a tuned value
  (a clock's turn count is fixed in advance, randomized or shown as a curve). Arms that train on them (seeded fixed
  points) or break rule 1 or 2 (deck-out wins paid 0, as for pilot-v2) are quarantined: nothing is built on them.
- **Evan's rules (binding):** (1) self-discovery: no human lists, hand-written bots, card-specific moves or
  game-specific shaping in training (a model trained on human data is a human prior); (2) game-agnostic: cards as
  features and text, legal options, results and the game's own end score only, carried to MTG; (3) learned and simple:
  one draft policy learned from real results and read through the pilot; a hand-built cap, acceptance rule or niche
  must be game-agnostic and simpler than what it replaces, or it goes to Evan; (4) his ideas first (§11).
- **The game's definition** (a clock, the round rule in training) is Evan's call. Per row 26 the walls' wins point at
  the process: the round rule and draws at T are evaluation oracles (§7); if they locate the fault, the loop seeks
  process changes with the same effect (a pilot or judge that wins prize races) instead of waiting on a rule change.

## 3. Scorecard
| Row (approved: plan-rediscovery, Evan row 10) | Readout | Target | Noise (A/A) |
|---|---|---|---|
| Pilot | Trainer groups on the lists (draw / search / disrupt / tempo) against an Energy copy | each > 0.55 | to calibrate |
| Pilot | win-this-turn puzzles attack-only / Trainer-first / PlusPower; strength vs SimpleBot on the lists | ≥ 90 / 85 / 90%; ≥ 0.90 | s1 RMS 0.025, bar 0.06 |
| Decks | median P / T / E of the best decks; staples a deck; archetypes at overlap ≥ 0.5 | each within 5 of 13.5 / 28 / 18; ≥ 7; ≥ 3 | top-12 L1 RMS 2.0-4.8; medians 1.3 / 1.4 / 0.8; staples 1.4; overlap 0.08 |
| Decks | draft head's incoming entropy; swing of median Trainers over 40 iterations | ≥ 2 nats; ≤ 5 | h_in RMS 0.38 |
| Meta | best decks against the lists, under a pilot that passes the pilot rows | ≥ 0.5 | SE 0.013 at 1,152 games |
| Judge (added 2026-10-21, approved with the method 2026-10-22) | JF1 the largest type's best decks vs the lists, both seats by the judge, 16 games a pair, same deals; JF2 its logit equilibrium on the 24 × 24 list matrix vs the field's shares (TV; not Nash LP at 32 games a pair); JF3 the pilot rows under its play; JF4 the audit of §7 | JF1 < 0.5 by 3 SE; JF2 inside its bootstrap spread | as Meta |

Shape and types are necessary, not sufficient (#114, #140); a drafted deck far above 0.5 against optimal lists points
at the judge. Each deciding readout gets an A/A from 3 reseeds of the current base before use (present bars: 2 forks at
160, one pair at 479), redone after each adoption; known measurement faults (#139's ending label) are flagged in use.

## 4. Rivals and the Matrix
Each open question keeps rivals and a catch-all at the head of `hypotheses.md`: **Q1**, why one wall type takes the
population; **Q2**, why runs from scratch collapse into Pokémon piles (H27, H45, H46). A rival names one link as the
cause, with a readout, an oracle swap and a demotion test fixed in advance (changed only by log entry). Q1's set:

| Rival | Claim (nodes; families) | Primary readout; noise | Oracle swap | Demoted if |
|---|---|---|---|---|
| E game | With no clock, stalling to deck-out pays; the lists are best under the round rule (N1; H01, H03, H04, H51-H53) | ending mix against list-mirror games under the same judge (deck-outs 27-35%, #149); share at a cap or limit; each side's pass and attack rates near it; deck-out RMS 0.08 | the STS round rule, or draws, at a T fixed in advance | under the round rule at T ≤ 50 with search on both seats, the walls keep ≥ 0.55 of the points |
| I inputs | With slot binding off, attached Energy reads as slot × 8 + copies (`rl/token_model.py:367`); both decklists are visible (N11; H57, H58) | the input against the true state, then drafted Energy and JF1 | true counts; decklists hidden | each fix leaves drafted Energy and JF1 inside their A/A bands |
| P pilot | The pilot plays tempo and prize races badly, so tempo decks lose their places (N2, N3, N10; H05, H06, H11, H14, H15, H19) | s1 by class (no positive control yet), Trainer panel, Elo vs the parent and pilot-v2 on fixed panels and deals; Elo σ ≈ 8.8, a reseeded no-change fork -13.3 [-20.1, -6.4] | play-time search on every move of a side; a strength ladder | the walls' score does not fall as play strength rises on both seats |
| J judge | A judge grown with the decks rates highest what it plays well; J1 co-adapted by playing the walls, J2 shaped by the deck-out payoff it trained under (N4; H18, H20-H23) | JF1-JF4; in the loop, selection choices changed vs the redraw null | a judge never trained on the population; search on both seats | a judge never trained on wall fields, but paid for deck-out wins, also rates the walls ≥ 0.55 |
| S selection | Mean-vs-field selection, noisy acceptance and a collapsing head give one type under any judge (N5-N8, N13; H24-H44) | moves vs the null (65-83 of 99 ungated, about 20 gated); fresh-game re-score of accepted moves; P / T / E of proposed, accepted and cut cards; h_in, h_out; types by game-agnostic clusters calibrated on the lists, and decks holding the two commonest non-staple cards; moves RMS 5.7, largest type gap ≤ 14 | paired or exact acceptance; the surrogate (§7) | selection keeps ≥ 3 types in a surrogate with a known multi-type equilibrium, and in the loop under a gated judge |
| X exploration | Human types sit across a valley of about 8-10 coordinated changes (N6, N7, N9; H27, H45, H46) | seeded: do human types hold; from scratch: attacks, endings, Pokémon count (noise to measure) | human archetypes as seeds (quarantined) | a seeded human field drifts to walls, or random starts reach human types |
| 0 other | none of these | | outside research (§12) | |

- **Readouts match the node:** a candidate is decided on its rival's readout, by one named evaluator; deck shape decides
  S and X arms, and in-loop E or J arms past their manipulation check, never P or I arms.
- **Links combine:** each rival is tested for sufficiency (fixing it alone moves the outcome past its band) and
  necessity (with the other fixes in place, undoing it brings the failure back). A supported conjunction gets a column
  (E+P, #147: search on both seats plus draws at 50-60 turns 0.44-0.46, each alone 0.57-0.60); a status resting on a
  linchpin row (E+P: 192 games, about ±0.10) is replicated before anything builds on it.
- **The Matrix:** a column per rival and supported conjunction, a row per crucial experiment: when queued each rival's
  band, when finished a mark per rival (+ inside its band, - outside, 0 no prediction), the LR (§9) and the log entry.
  Rows every rival fits leave it. The **leading rival** is the live one best supported by diagnostic rows.
- Results carry their conditions (judge, game rule, fork, recipe). Only exclusions are conclusions. A rival is split
  only when an affordable experiment separates its parts (J into J1, J2); rivals none separates are merged.

## 5. The archive: grades, distinctness, coverage
`hypotheses.md` is an archive over node × mechanism: a family (H01-H69, new from H70) is a cell, its tests (entry,
configuration, result, grade) its members, the most adequate the elite; facts S01-S30 and anomalies A1-A9 continue.
- **Grades:** A, powered (LR ≥ 10 reachable, §9), 2 seeds an arm beside a concurrent control or a probe with a stated
  SE, the node's horizon, manipulation check passed, no named confound, for N5-N7 a judge that passes the gate; B, one
  seed or one named confound; C, underpowered, stopped before its horizon, killed by machine, or inert. Only A
  establishes or refutes, a refutation naming its configuration ("refuted for `--draft-ent 0.05` on a reset head from
  460"); B supports or weakens and can promote to replication; below A the verdict is "not supported as tested" (dose,
  horizon, judge, fork, seeds), and C counts as untested.
- **Two routes in:** a candidate opens a cell (a mechanism the ledger lacks, predicting differently from every family)
  or becomes its cell's elite by fixing a named inadequacy (power, seeds, horizon, confound, start, judge, dose ≥ 2×).
- **Near-duplicates are rejected** by descriptor (same cell, lever, direction, dose range, start class, judge and
  horizon as a recorded test, no inadequacy fixed; a new name or "X's flags plus Y" is no difference) and by prediction
  (every live rival predicts what its nearest past test showed, as for the 8 pilot-training changes under one
  co-adapted judge, #130-#147). List the 3 nearest tests, grep the log, notes and commits, write the difference into
  the record; date each rejection under its family. Do-not-repeat entries name exact configurations, never a whole
  mechanism; a null under a confound or from an inert treatment leaves the variant open.
- **Coverage table:** nodes × levers (game rule, inputs, pilot data, objective, search, judge, selection, proposals,
  population, coupling, start, measurement) counting A, B and C tests; empty or C-only cells are gaps (§8).

## 6. The cycle and the choice
A cycle: **record** (log, then ledger) → **score** results against their pre-written bands → **check** triggers (§12)
and floor (§8) → **generate** a candidate that could demote each live rival and the experiment that splits the two
leading ones, plus Evan's requests, untested variants, gaps, outside output → **filter** (§2, §5, admissibility) →
**allocate** → **launch** beside a concurrent control → **monitor** (§9) → **close** (§13, §14).
- **Allocation order:** (a) Evan's ideas; (b) running candidates to their horizon; (c) infrastructure that unblocks an
  admissible experiment, and A/A where a deciding readout lacks one; (d) the floor while unmet (§8); (e) admissible
  candidates by rivals they can demote per desktop-hour (dh: a screen slot-hour; CPU probe 0.25 dh an hour, GPU probe
  0.5, agent-hour 1), cheapest layer first (§7), upstream (E, I, P, J) before S and X on ties.
- **Admissible (Platt; Heuer):** at least two live rivals or conjunctions predict disjoint bands on the primary readout,
  centres at least 2 noise units apart (A/A RMS of the arm-control difference for screens, SE for probes), each band
  citing the fact or result it rests on. Exempt but still banded: A/A, unblocking infrastructure, Evan's ideas, floor
  candidates. Not admissible: the incumbent plus one lever when every rival predicts the same relapse; re-measuring
  what every rival predicts alike (13 population pilots as judges, 0.68-0.83); S or X deck readouts under a failed gate.
- **Disprove the leader first.** **No idle slot, no drift:** a slot no admissible candidate fills runs a replication
  seed of the leading result, an A/A seed or a floor candidate, in that order, never a new flag on the incumbent.
- **Act, test or drop** (Pauker and Kassirer) on a pending decision (adopt into R0, build, end a line, ask Evan): with p
  the judged chance acting is right and C, L_wrong, L_miss the dh costs of the cheapest settling test, a wrong act and a
  miss, act if p ≥ 1 - C/L_wrong, drop if p ≤ C/L_miss, else test (adoption, C 3, L_wrong 30, L_miss 20: act at 0.9,
  drop at 0.15). A cheap, reversible change right under every rival (a measurement, a bug fix) needs no screen.

## 7. Experiment design
- **Cheapest layer first:** offline probes on frozen checkpoints and fixed deals; testbeds (pilot panels and puzzles;
  JF1-JF4; a CPU surrogate metagame with known multi-type equilibria, judge bias growing with a type's share, binomial
  noise); screens last. A probe testing a screen's premise for under a fifth of its cost goes first.
- **Oracle swaps** test a link by substituting its oracle (§4), offline first; interacting links are crossed at least
  2 × 2 (a link excluded alone is not excluded in conjunction, §4) and factorials replace one-factor-at-a-time screens.
- **Delta debugging** (Zeller): between disagreeing configurations (pilot-v2 at 0.26 vs population pilots at
  0.68-0.75; an arm and its control), apply half the differences to the passing one and recurse into the half that
  brings the failure back, coarse first, with bands fixed before the first test (JF1: fail ≥ 0.55, pass ≤ 0.35).
- **Fixed-point test:** a loop seeded with the human field (quarantined) that drifts to walls puts the fault upstream
  (E, I, P, J); one that holds while random and wall starts never reach it puts it in S or X. Offline first: the payoff
  matrix of human archetypes, walls and population types under each judge, then its fixed point.
- **Judge gate:** before a judge drives selection, audit its empirical game over the panel (edges resolved adaptively,
  at most 64 games a pair; the walls' Condorcet status; sink components). Where the walls are a resolved Condorcet
  winner, schemes keep other types only by construction (caps, niches), never by winning: S and X arms there are read
  only on mechanism readouts (acceptance noise, re-score regression, proposal and cut composition).
- **Power and manipulation:** before launch, compute the games, seeds and iterations that make LR ≥ 10 reachable at
  the band centres, or redesign; state what the treatment must change by iteration 3 (searched games flip selections
  beyond the redraw null; a limit binds in a stated share of games) and dry-run new selection rules on logged games.
  `scr-jsearch479` fails both: 2.02 searched games a candidate, 6 changed selections against 15.5 from redraws (#149).
- **Controls and seeds:** a control is concurrent (same fork, recipe version, code hash, workers and `--reseed`;
  `scr-t60gate479` was not one); a batch is one control and up to two arms; one seed only promotes to replication, and
  a claim, adoption or stacking base needs 2. Probes pair games on identical deals; pairing `--select` is a build.

## 8. Exploration floor
- Every live rival keeps a queued candidate that could demote it; a rival without one fires O2 (§12).
- Starts are escape (forked from a wall state, as 460 and 479) or prevention (fresh, wide decks, pre-collapse). Of every
  4 screens at least one is a prevention start and one goes to a coverage-table gap off the leading rival's nodes (one
  may be both); the critic's gaps seed the table: N8, N9, N13, unfinished-game payoff, cut choice, who decks are scored
  against, prompt decisions, meta-level solution concept, Energy-count input, open decklists.
- At most 2 of 3 slots run the incumbent's lineage; at most half of any 10 screens fork one state; every third adoption
  into R0 is followed by a from-scratch check run (plan-rediscovery).

## 9. Kill rules and evidence
- **Looks** at 3, 5, 10, 15, 20 and 30 iterations; any look can stop a run, none alone calls success. End states:
  **decided** (past the horizon, the readout holds for two looks in a band that demotes a rival, the control's band
  included; one seed promotes to replication); **futile** (the bands can no longer separate within budget); **harmful**
  (over 2 noise units worse than the control at two looks running); **inert** (manipulation check failed: "untestable
  as built"); **killed by machine** (no verdict: relaunch or close).
- **Evidence:** with band centres m1, m2 and noise s, an observation x per seed (arm minus control over the window)
  gives LR = exp(((x - m2)² - (x - m1)²) / 2s²) for rival 1 over 2, multiplied over seeds; ≥ 10 supports rival 1,
  ≤ 0.1 rival 2. At a band centre LR = exp(δ²/2s²), δ = |m1 - m2|: 10 at δ ≈ 2.15 s (1.5 s on two seeds).
- **Horizons:** drafting, selection and population arms, and in-loop judge or game-rule arms past their manipulation
  check, run at least 10 iterations; relapse is smoothed top-12 distance above its minimum + 5 for 5 iterations, or the
  largest type past 50; no success before 15 iterations past the arm's best and the control's relapse window (one type
  re-forms 10-16 iterations after a 479 fork, S03). Pilot and input arms run 2-3 segments of 10, stopped early only
  when clearly worse (Elo below about -18, s1 down 0.06), warm-started unless identity (#98). From scratch: stop if
  prize endings are under 10% at iteration 30 (#71). Probes stop at their SE target or when no outcome changes the call.
- **Evan's rule** (stop what is not making progress, then and there) applies at every look on the run's own node
  readout: decided, futile, harmful and inert runs stop at once. A run stopped before its horizon closes as grade C
  ("no effect at this dose, as run" for a stall), never as refuted, with an exact do-not-repeat for its configuration.

## 10. Recipes, launches and the record
- **`notes/recipes.md`:** R0 is the lab's adopted recipe at retirement (lr 2e-4, 2 PPO epochs, 6 changes a draw,
  result-only draft reward, draft lr 3e-4, fading shaping 0.1, deck-free pilot); other components carry flags, H id,
  source entry and status (adopted, replicated, single seed, inert, refuted); stacked screen recipes are frozen legacy.
- **Stacking cap:** a screen is a registry recipe plus at most 2 unadopted components; a component joins R0 (as R1,
  ...) only on an A-grade pass on its node's readout and leaves when it shows no effect beyond A/A (Occam). R0 moves
  decks by forced draws (#127's ratchet), so screens add an acceptance rule; the gate (#140, one seed) is unadopted.
- **Launch:** `screen.py` takes a candidate id and a recipe and refuses a launch without them or with a repeated flag
  (`scr-gate479` passed `--turnover-every` twice); until it does, the record is written by hand first. Code defaults
  equal R0 or say otherwise in their help strings; hand-launched smokes and evaluations pass the recipe in full.
- **Names:** candidates `Cnn`, never reused; runs `runs/screens/C07-h23.2-479-s1` (candidate, family variant, start,
  seed), `C07-ctl-R0-479-s1`, `C08-aa-R0-479-s3`, `runs/probe/C07-<what>/`; old `scr-*` names stay.
- **The record**, in `screen.jsonl` or the probe header and in the Queue, before launch:

      C07 · screen · N4, N10 · H23.3, H52.1 · rivals J, E · Evan: no · escape (479) · cost (dh) · rules 1-3, MTG
      Design: arms, recipe + delta, seeds, deals, concurrent control; why no cheaper layer splits the rivals
      Readout: primary, window, noise, power; manipulation check by iteration 3; kill: looks, horizon; list reads
      Bands: J ...; E ...; 0 ...  Excludes: J if ...; E if ...  Distinct: 3 nearest tests, what is new, which rival

## 11. Evan's ideas first
- Each message gets a row in `notes/evan-requests.md` the same turn (tried, partly, not tried, rule or answered, with
  its candidate id). His ideas head the Queue, ahead of floors and ranking, tried fully (the strongest version plus a
  variant, at their node's horizon) and exempt from admissibility only, so their records still update the Matrix.
- If an idea matches a recorded test, tell him which and run its closest untested form unless he asks for the repeat;
  if it meets a binding rule, tell him with the H id and ask; never drop one silently. His decisions (training rules,
  commits, deleting run data, borderline rule calls) go in README Next with one line of evidence; work goes on (row 26).

## 12. Looking outside the system (Evan, rows 32-33)
Outside means literature and theory, the game's history and rules, or a question to Evan. A round runs beside the
slots (1-3 agent-hours), at each periodic review (§15) and whenever one of these fires:
- **O1 anomaly:** a robust result outside every live band (it gets an A id) or against a standing fact, unexplained
  after one targeted internal check; or 2 of the last 3 results outside every band (suspend the ranking meanwhile).
- **O2 exhaustion:** the leading rival has no admissible candidate (no untested variant predicted to move its readout
  past the noise), the catch-all fits the last 2 robust results best, or every named rival has failed a prediction.
- **O3 premise:** a decision hinges on a fact about the real game or the ground truth that no run can produce (turns in
  a 20-minute 2000 round; how stall decks fared in 1999-2000 events).
- **O4 judge dead end:** the walls are a resolved Condorcet winner or the only sink under every affordable judge (§7):
  stop meta-level screens; what is left is a stronger or independent judge, the pilot, or (Evan's) the rules.
- **O5 capability gap:** the top candidate needs an unbuilt technique whose design choices matter: how-to research.
- **O6 stall or repetition,** firing twice running or with another trigger: 3 closed candidates with no exclusion and
  no scorecard row past noise; 3 graded nulls in one cell; or 2 of the last 5 proposals near-duplicates.

Exhaustion, stall and repetition rounds wait while a cheap admissible crucial experiment for the leading rivals is
queued; anomaly, premise and dead-end rounds run in parallel. A round starts from a ledger brief (rivals, Matrix,
anomalies, gaps, do-not-repeat lists, sources already read) and one sharp question, and returns, under its own log
entry, fact-checked ledger rows with sources, not a report: new rivals, families, variants or C entries, each with
bands. Its yield is how many prove diagnostic (LR ≥ 10) within two tests; after 2 dry triggered rounds in a row O6
needs two firings (O1-O4 still act alone), after 3 only the periodic round runs. Replay the thresholds over #100-#147
before relying on them: they should fire near #116 and within #127-#137, well before #144, and not on most entries.

## 13. Logging, README and evan-requests
- **Log (CLAUDE.md format):** one entry per finished todo (builds, launches, runs ended in any state, outside rounds,
  declutter steps); the plan-item field holds Plan heading and candidate (`### #151 · 2026-10-22 · A5 C07 · <todo>`).
  **Evidence** gives readouts against each rival's band with noise and LR; **Found** opens with the ledger change
  (`Ledger: H23 inconclusive -> supported (B); C07: J -, E +`) and new A or S ids; **Next** names candidate ids. No
  launch while a finished run, probe, build or round is unlogged; no file cites an unwritten entry.
- **The ledger** changes in the same turn, from the entry, never from memory; it indexes the log by mechanism and adds
  no claim the log lacks (CLAUDE.md's guard against compounding errors).
- **README:** CLAUDE.md's recursive rules stand; **Next** is the Queue's top 3-6 in allocation order (id, one line,
  rivals split), decision-for-Evan lines among them, never an item the ledger marks tested. A **milestone** is a
  scorecard row first meeting its approved target in a replicated run: it closes a README block, and when a Plan
  heading's exit is met (A5: the from-scratch run on the whole scorecard) the heading is marked done.
- **`evan-requests.md`:** each row is updated when its candidate closes; "Not tried yet" lists every open idea.

## 14. Decluttering
- **One home per fact:** history in the log; mechanisms, rivals, facts, coverage and Queue in `hypotheses.md`; flags in
  `recipes.md`; why a run exists in its record; rules here; superseded documents carry a banner. **Close where it
  tempts:** a closed family or candidate is marked closed wherever a reader would find it open (lab card, run folder,
  plan, memory note, evan-requests row, README Next, code help string).
- **Index, do not move:** fork and resume files stay put (`runs/lab/main/seg_0460.pt`, the 479 population);
  `runs/screens/INDEX.md` maps each folder to candidate, entry and verdict or "not read"; deleting run data needs Evan;
  retired machinery keeps a STOP file with its reason.
- Contradicted memory notes, README lines and plans are fixed in the same cycle; uncommitted work is listed each session
  and committed only on Evan's go-ahead; one-off cleanups are C entries. Each session start includes a clutter look:
  nothing resumable by accident, registry and code defaults in step, no dangling citations.

## 15. Periodic review and checking the method
Every 10 closed candidates or at a milestone: recompute the effort map and coverage table; queue, or defer in writing,
each rival or family whose distinct untested variant has waited 20 candidates; re-check statuses changed since the last
review (verification corrected 50 of 69, and 7 of 29 refutations); recompute early-vs-final rank agreement, shortening
a horizon only where it reaches ρ ≈ 0.7; count the finished Matrix rows inside some live rival's band (target ≥ 70%;
below it, widen bands and fire O1); run the periodic outside round. The method is itself a family (N12): over the next
8 experiments at least 2 rivals or conjunctions should be excluded or shifted by LR ≥ 10 (#128-#147 gave about 3
diagnostic results, #137, #139, #147, in about 25 runs and probes); over 12, at least 3 new families and near-duplicates
under 20% of proposals. If after 8 the exclusions per desktop-day do not beat #128-#147's, keep the Matrix as
documentation, stop gating launches on admissibility (the archive check, floor and kill rules stay) and log why. All
numbers here are starting values, changed only by a log entry.
