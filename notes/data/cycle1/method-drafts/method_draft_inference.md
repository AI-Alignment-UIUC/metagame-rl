# Method: strong inference over the hypothesis ledger (2026-10-21)

Replaces `notes/plan-lab.md` (the lab, stopped since 10-20 23:05) and `notes/plan-rediscovery.md` (its approved targets
stay in §3). In #128-#149 the research loop had the model's failure: about 25 screens each added one flag to the
incumbent (19 of 27 reuse a recipe, 25 of 27 fork from the wall states 460 and 479) and were read on a noisy deck
readout; "relapses like the control" is what every live explanation predicts, so they excluded nothing. Probes built to
split explanations did: the pilot pairings (#137), human-side search (#139), search crossed with draw limits (#147). So
rivals are kept side by side, every run must be able to exclude one, and each is read on its own link's readout.

## 1. Session start
1. Read README Status, the last three log entries, new rows of `notes/evan-requests.md`, and the Matrix and Queue of
   `notes/hypotheses.md`. A new message from Evan gets its row now; an idea of his heads the Queue (§12).
2. Machine: GPU at most 80%, at most 3 screens, free RAM, `runs/lab/STOP` in place, no orphan processes.
3. For each live run, read its record (§13) and apply its kill rule (§10). Log anything finished but unlogged first.
4. Score new results into the Matrix (§5, step 2), then check the outside-research triggers (§11).
5. Fill free slots from the Queue, top first, under the floor (§12), distinctness (§9) and admissibility (§6); write
   each record before launch. Before stopping, the log, `hypotheses.md`, README and `evan-requests.md` agree.

## 2. Goal and ground truth
- **Goal.** From random decks, with nothing human in training, the loop drafts and plays a metagame matching the 2000
  STS field: median 13.5 Pokémon / 28 Trainers / 18 Energy (Pokémon 10-18, Energy 14-25), 8 archetypes (Wigglytuff 10
  lists, Haymaker 7, Sponge 2, five singletons; effective number 3.6); then, unchanged, Worlds 2005 (sealed) and Magic,
  so rules and readouts are stated without card names except legacy cross-checks.
- **Evan's premise defines failure:** the lists are optimal, so a consistent deviation (more Energy, fewer Trainers, one
  type) means part of the process is wrong. The rivals of §4 compete over which part; the engine's missing clock (the
  lists were built for 20-minute rounds) is one (E). Changing the game's rules in training is Evan's call.
- **Evaluation and diagnosis only.** The 24 lists may be an evaluation panel, a judge-fidelity test or a diagnostic
  seed (§7), never training data, a training opponent, part of a recipe or a tuning target (a clock's turn count is
  fixed in advance, randomized or reported as a curve). Runs that use them or break rule 2 are quarantined: no recipe,
  checkpoint, judge or fork comes from them. Kill rules prefer human-free readouts; each list-based decision is counted.

## 3. Scorecard (each milestone and adoption; evaluation only)
| Row | Readout | Now | Target | Noise |
|---|---|---|---|---|
| Shape | median P / T / E of the population and of the top 12 by z; L1 to 13.5 / 28 / 18 | population 13-14 / 25-26 / 20 (`scr-jsearch479`, 494); main line 8 / 15 / 37 (430) | each within 5, held 40 iterations | A/A RMS 2.0-4.8 (under 5 is noise); jitter SD ~1.9; read 3-iteration means |
| Types | largest type and effective number by a game-agnostic descriptor (card-count clusters), also computed on the 24 lists; share of decks holding the population's top card pair | one type; 53-96 of 99 decks hold Chansey + Snorlax in the 460 and 479 forks | the 24 lists' own values (effective number 3.6) | largest-type A/A gaps 2-14 decks |
| Archetypes | card-identity distance of each top deck to its nearest human list (to build) | none (walls) | ≥ 3 archetypes inside the lists' own spread | to measure |
| Judge and meta | JF1: the walls against the 24 lists, both seats played by the judge, 16 games a pair, same deals; JF2: the judge's equilibrium over the 24 lists against the field's shares; the best drafted decks against the 24 lists under a gated judge (§7) | JF1 0.68-0.75 (population pilots), 0.26 (pilot-v2), 0.44-0.46 (search on both seats + draws at 50-60, 192 games); JF2 logit TV 0.10-0.25 (population pilot) | JF1 below 0.5 by 3 SE; JF2 inside its bootstrap spread; drafted best decks ≥ 0.5 | SE ≈ 0.013 at 1,152 games, ±0.10 at 192; Nash unstable at 32 a pair |
| Pilot | competence s1; puzzles attack-only / Trainer-first / PlusPower; Trainer groups against an Energy copy; head-to-head with pilot-v2 on the human lists | 0.43-0.48; 86-94 / 58-61 / 31%; 0.36-0.52 (search, disrupt, tempo); -45 to +30 Elo by pilot | ≥ 90 / 85 / 90%; every group > 0.55; not behind pilot-v2 | s1 A/A RMS 0.025, bar 0.06; Elo σ ≈ 8.8 a fork |
| From scratch | endings and shape of a fresh run at 40 / 80 / 160 iterations | Pokémon piles, 85-99% deck-outs | the shape and type targets | to measure |

Targets approved with plan-rediscovery (Evan, row 10) are kept. A milestone is a row first meeting its target in a
replicated run; it closes a README block. A readout without an A/A from at least 2 reseeds of the current recipe gets
one before it decides anything, and A/A is redone after each adoption (the lab's bars come from two forks at 160).

## 4. Rivals, readouts and the Matrix
The failure is a chain of links (analysis §1); each rival names one link as a cause. Links combine, so each rival is
tested for being **sufficient** (fixing it alone moves the outcome past its band) and **necessary** (with the other
fixes in place, undoing it brings the failure back), on its own node's readout, with an oracle and a demotion test.

| Rival | Claim | Nodes; families | Primary readout; noise and horizon | Oracle swap | Demoted if |
|---|---|---|---|---|---|
| E game | With no clock, stalling to deck-out pays; the lists are optimal only under the round rule | N1, N10; H01, H03, H04, H51-H53 | endings (prize, no Pokémon, deck-out, cap, time); share of games at a limit; each side's pass and attack rates near it; deck-out share A/A RMS 0.08 | the STS round rule at a T fixed in advance; draws at T | under the round rule at T ≤ 50 with search on both seats, the walls keep ≥ 0.55 of the points |
| I inputs | Inputs bias play: with slot binding off, attached Energy reads as slot×8 + copies (`rl/token_model.py:367`); both decklists are visible | N11, N12; H57, H58 | the input against the true game state, then drafted Energy and JF1 | true counts; decklists hidden | the fix leaves drafted Energy and JF1 inside their A/A bands |
| P pilot | The pilot plays tempo and prize races badly, so tempo decks lose their places | N2, N3, N10, N11; H05-H06, H11, H14-H15, H19 | s1 by class; Trainer groups; head-to-head on fixed panels (human lists, walls, wide decks) against the parent and pilot-v2; credit by decisions to the end. s1 has no positive control yet (score a4-tok, pilot-v2, the anchored pilot first); a reseeded no-change fork was -13.3 Elo [-20.1, -6.4], so 2 forks or more; 2-3 segments of 10 | play-time search on every move of a side; a strength ladder | the walls' score does not fall as play strength rises on both seats |
| J judge | A judge grown with the decks rates highest what it plays well (F2) | N4; H18, H20-H23 | JF1, JF2, JF3 (puzzles and Trainer panel under its play) and the judge audit (§7); in the loop, the selection choices it changes against the redraw null; SE 0.013 at 1,152 games, by power | a judge never trained on the population; search on both seats | a judge never trained on wall fields, but paid for deck-out wins, also rates the walls ≥ 0.55 |
| S selection | Mean-vs-field selection, noisy acceptance and a collapsing head give one type under any judge | N5-N8, N13; H24-H44, H67-H69 | moves an iteration against the null (65-83 of 99 move ungated); fresh-game re-score of accepted moves; P / T / E of proposed, accepted and cut cards; h_in, h_out; types. h_in A/A RMS 0.38, moved 5.7; ≥ 10 iterations and 1.5 relapse times past the best | paired or exact acceptance; the surrogate testbed (§8) | selection keeps ≥ 3 types in a surrogate with a known multi-type equilibrium, and in the loop under a gated judge |
| X exploration | The human types sit across a fitness valley of about 8-10 coordinated changes | N6, N7, N9; H27, H45, H46 | from seeds, whether human types hold; from scratch, attack rate, endings and shape; 40-160 iterations | human archetypes as seeds (diagnostic) | a seeded human field drifts to walls, or random starts reach human types |
| 0 other | none of these | all | | outside research | |

Deck readouts are primary only for S and X and never stall an E, I, P or J run. A conjunction gets its own column once a
result supports it: E+P now (search on both seats with draws at 50-60 turns: 0.44-0.46; each alone 0.57-0.60; #147).

**The Matrix** heads `hypotheses.md`: a column per rival and conjunction, a row per diagnostic result and per queued
experiment. A queued row holds each rival's predicted band; a result row holds Heuer's marks (CC, C, N, I, II), its log
entry and its diagnosticity (how far apart the best- and worst-fitting rivals' likelihoods are: high, low, none). Rows
consistent with every rival leave the Matrix and stay as tests of their family. Each rival has a status line (live,
sufficient, necessary, excluded as sole cause, excluded at the doses tested) naming the rows that set it; the live rival
best supported by diagnostic rows is the **leading rival**. A status resting on one or two **linchpin rows** (E+P rests
on 192 games, ±0.10) is replicated or powered before anything is built on it. Results carry their conditions (judge,
game rule, fork state, recipe): a deck result under a judge that fails the gate (§7) cannot exclude S or X.

## 5. The cycle (from a result or a free slot to the next launch)
1. **Read** each result against the bands written before its run.
2. **Score** it: marks per rival, diagnosticity, exclusions in words ("J excluded as sole cause at this dose") in the
   Matrix and the H entry. A robust result (≥ 3 SE, or replicated) outside every band becomes an A id. Check §11.
3. **Generate,** for each live rival, a candidate that could demote it, and for the two leading rivals the experiment
   that splits them: from untested variants in `hypotheses.md`, empty Matrix cells, outside rounds and Evan.
4. **Filter** by distinctness (§9) and admissibility (§6); **rank** by diagnosticity per desktop-hour, cheapest layer
   first (§8), upstream links (E, I, P, J) before downstream ones (S, X); then apply the floor (§12).
5. **Design** and write the record (§13); **launch** within the machine limits; **monitor** by the kill rule (§10).
6. **Close:** log entry, `hypotheses.md` (status, tests, exclusions, do-not-repeat, Matrix row), README Next (§13).

## 6. Crucial experiments only (Platt; Heuer)
- **Admissible:** at least two live rivals (or conjunctions) predict disjoint bands on the primary readout, separated by
  more than its noise (2× A/A RMS for screen readouts, 3 SE for probes), so every outcome demotes something; starting
  bar, a predicted likelihood ratio of about 10. **Exempt, but still written with bands:** A/A and calibration,
  infrastructure that unblocks an admissible experiment, Evan's ideas (§12), the floor's slot.
- **Not admissible:** the incumbent plus one lever when every rival predicts the same relapse; re-measuring what every
  rival predicts alike (about 13 population pilots as judges, all 0.68-0.83); deck-type readouts of a meta-level arm
  under a judge where the walls are a resolved Condorcet winner (§7).
- **Disprove the leader first:** the experiment the leading rival is likeliest to fail comes before those that can only
  confirm it; for a supported conjunction, test each part's necessity. A surviving rival is split into sub-rivals with
  their own oracles (Platt's recycling), e.g. J into "co-adapted by playing the walls" and "shaped by the deck-out
  payoff it was trained under".
- **Only exclusions are conclusions;** anything else is provisional and is replicated before anything is stacked on it.

## 7. Oracle swaps, delta debugging, the fixed point and the judge gate
- **Oracle swaps** test a link by substituting its oracle (§4): offline first, then in a component testbed, then in a
  screen. Links that may interact are crossed, at least 2×2: draw limits and search each failed alone (#143, #146) and
  together put the walls below the lists (#147), so a link excluded alone is not excluded in conjunction.
- **Delta debugging** (Zeller's ddmin; dd+ for interference): when two configurations disagree (pilot-v2 at 0.26
  against population pilots at 0.68-0.75; the bare recipe against the incumbent; an arm against its control), apply
  half their differences to the passing one and recurse into the half that brings the failure back, splitting coarse
  differences ("training decks") first. Bands are fixed before the first test from the two references and the SE (for
  JF1 here: FAIL ≥ 0.55, PASS ≤ 0.35, unresolved between). Diagnostic arms may break rule 2 (deck-out wins paid 0).
- **The fixed-point test** splits the chain in two: seed the loop with the human field (diagnostic, like #131's human
  practice). If it drifts to walls the fault is upstream (E, I, P or J); if it holds but random and wall starts never
  reach it, it is S or X. Offline first: the payoff matrix of human archetypes, walls and population types per judge.
- **The judge gate:** before a judge drives selection, its game over that panel is audited (edges resolved adaptively,
  at most 64 games a pair; the walls' Condorcet status; sink components). Where the walls are a resolved Condorcet
  winner, no selection or diversity scheme can keep another type, so S and X arms are read there only on mechanism
  readouts (acceptance noise, re-score regression, proposal and cut composition). If so under every judge we can
  afford, meta-level screens stop and T5 fires (§11).

## 8. Experiment design
- **Cheapest layer that discriminates:** (1) offline probes on fixed deals and frozen checkpoints (minutes on the GPU;
  hours on the CPU when searched, about 1.6 s a searched game); (2) component testbeds: pilot panels and puzzles, and a
  CPU surrogate metagame (known multi-type equilibrium, injected judge bias, binomial noise) for meta algorithms;
  (3) screens (about 6 minutes an iteration, 3 slots), each stating why no cheaper layer splits its rivals.
- **Power before launch:** compute the games, seeds or iterations the bands need; redesign or drop rather than run
  underpowered (`scr-jsearch479` searched 2.02 games a candidate and changed 6 choices in all, 15.5 by redraw alone).
  **Show the treatment is active** before reading a null: code path hit, choices changed above the redraw null.
- **Controls** run at the same time, from the same fork state and code, and differ only in the tested factors. The run
  is the unit: 2 seeds or more an arm before a result is built on; paired deals (common random numbers) wherever decks,
  pilots or judges are compared. **Factorials** replace one-factor-at-a-time when levers may interact; a screening
  design over the incumbent's flags waits for their A/A. **Start states:** prevention is tested from fresh or
  pre-collapse states (460 and 479 test escape); at most half of a cycle's screens fork from one state.

## 9. Distinctness and stacking
- **Distinct means some rival predicts a different outcome** for the candidate than for its nearest past experiment.
  Before queueing: read its nodes' families and do-not-repeat lists in `hypotheses.md`, grep the log for its key terms,
  list the three nearest past experiments (log refs), and name the never-varied factor (node, mechanism, judge, start
  state, dose range, horizon, seeds, readout) and the rival that predicts it matters. Without both it is rejected.
- **A new name for a tested mechanism is a repeat.** The chief repeats: changing what the shared pilot trains on while
  the same co-adapted pilot judges (8 times, #130-#147); near-uniform draws from a pool that is 81% Pokémon (at least
  6); population pilots re-measured as judges (about 13). A null under a confound or from an inert treatment does not
  close a family: record the confound and keep the variant.
- **Stacking cap:** a screen is a named recipe plus at most 2 flags. A flag joins a recipe only after a replicated
  effect on its node's readout, and leaves at the next adoption if none was measured. Recipes live in
  `notes/recipes/<name>.json`, each flag with its value, source log entry and status. Argparse defaults (they differ
  from the adopted recipe in swaps, draft margin, lr, draft lr, epochs and shaping) and `screen.py`'s base (the lab's
  pre-#127 `main_args`) are not recipes.

## 10. Kill rules
- Every record carries its kill rule. A run ends **decided** (its readout entered a band that demotes a rival, either
  way), **futile** (the bands can no longer separate within budget) or **inert** (the treatment did not act: "untestable
  as built", not "refuted").
- **Horizons by node:** selection and drafting arms run at least 10 iterations and 1.5 relapse times past their best
  (distance relapses 4-9 iterations after its minimum; one type re-forms in 10-16); pilot arms run 2-3 segments of 10
  and stop early only when clearly worse on the pilot readout; probes stop by power.
- **Evan's stall rule** (CLAUDE.md): a run not making progress stops then and there, meaning its primary readout stayed
  inside the control's A/A band over its node's horizon, or it is futile or inert. It is recorded as "no effect at this
  dose", with a do-not-repeat entry for that exact configuration. Each milestone, recompute each readout's
  early-against-final rank agreement from the screen logs; shorten a horizon only where it reaches about 0.7.

## 11. When to research outside the system (Evan, rows 32-33)
Open an outside round (literature, theory, the game's history and rules, or a question to Evan) on any of:
- **T1 exhaustion:** the leading rival has no admissible candidate left (every untested variant of it is predicted to
  move its readout by less than the noise);
- **T2 anomaly:** a robust result outside every band, or an A id unexplained for 2 cycles;
- **T3 catch-all:** every named rival has an I or II on a robust row, or none predicted the last 2 robust results;
- **T4 premise:** evidence puts the environment or the ground truth in question (now: how many turns a 20-minute 2000
  round allowed, and how stall decks fared in 1999-2000 events);
- **T5 judge exhaustion:** the walls are a resolved Condorcet winner under every affordable judge (§7);
- **T6 capability:** the next admissible experiment needs a method whose design choices matter (how-to research first);
- **T7 stall, T8 repetition, T9 degeneration,** when two fire together or one fires twice running: 3 cycles with no
  exclusion and no scorecard row moving past noise, or 3 null variants of one mechanism; 2 of the last 5 proposals
  rejected as repeats; at most one of the last 8 changes corroborated a prediction made in advance;
- **periodic:** each milestone or every 10 cycles, whichever comes first.

Not when a cheap, admissible, untested crucial experiment exists for the leading rivals: run it first. A round runs
beside screens, gets a brief (Matrix, anomalies, the node's families) and returns fact-checked rivals, mechanisms or
diagnostics as H or C entries; its yield is how many prove diagnostic. After two empty rounds, only T1-T6 open one.

## 12. Exploration floor; Evan's ideas first
- Every live rival keeps a queued candidate that could demote it; a rival without one fires T1.
- Over any 3 cycles, at least one screen slot in five (a starting value) goes to the least-tested live rival or node of
  the last 5 cycles (now N8, N9, N13, the payoff in N1, and N4 inside the loop, which has had two interventions); the
  effort map by node is recomputed each milestone. At most 2 of 3 slots run arms of the incumbent recipe's lineage, and
  each milestone one slot tests prevention from a fresh or pre-collapse state.
- **Evan's ideas first:** each heads the Queue in its strongest version plus a variant and is tried fully. It is exempt
  from admissibility only; its record, bands, readout and kill rule are written as for any run, so it still updates the
  Matrix. If it repeats a do-not-repeat configuration or meets a binding rule, tell him with the H id and ask; never
  drop it silently. A cause he states is taken as given. Decisions only he makes (rule changes, the round rule in
  training, commits, engine changes) are queued as decision-for-Evan candidates with one sentence of evidence each.

## 13. Objects, names, the record and logging
- **`notes/hypotheses.md`** is the one index: nodes N1-N13, standing facts S01-S35, anomalies A1-A9 (new from A10), the
  Matrix, families H01-H69 and new ones from H70 (`### H27 · N6 · supported (moderate) · name`: mechanism, verdict,
  tests with log refs, exclusions, do not repeat as exact configurations, untested variants), and the Queue. Status
  words: established, supported, partly-supported, adopted, weakened, refuted, inconclusive, underpowered, untested. An
  entry changes only with a log entry that cites it.
- **Candidates `Cnn`**, numbered once and never reused: one experiment (diagnostic, intervention, infrastructure,
  decision-for-Evan or outside-research) testing named H ids; one on an unindexed mechanism opens an H. **Runs are named
  by C id** (`runs/screens/C07-<arm>-s<seed>`, `runs/probe/C07-<what>.json`); older `scr-*` runs keep their names.
- **The record** sits in `screen.jsonl` or the probe file's header and in the C entry; `screen.py` refuses a launch
  without it or with more than 2 flags beyond the named recipe:

      C07 · diagnostic · N4, N10 · tests H18, H52 · rivals J, E · Evan: no
      Design: arms, fork state, recipe + delta, seeds, deals; why no cheaper layer splits them
      Readout: primary and window, secondary; noise and power
      Bands: J ...; E ...; other outcomes ...   Excludes: J as sole cause if ...; E if ...
      Kill: decided / futile / inert conditions; horizon
      Distinct from: H ids, nearest log refs, new factor, the rival that predicts it matters. Cost; rules; consultations

- **Logging** follows CLAUDE.md: one entry per decided experiment, outside round or declutter step, titled with its C
  and H ids (`### #151 · 2026-10-22 · C07 · H18, H52 · ...`); **Evidence** is the readout against each rival's band,
  **Found** what was excluded (or "no exclusion" and why) and any new A id. In the same turn: `hypotheses.md`, then the
  README status, whose **Next** is rebuilt from the Queue: its top 3-6 items with C ids and the rivals each splits.

## 14. Decluttering
- One place per question: what was tried, `hypotheses.md`; flags, recipes; why a run exists, its record; history, the
  log. Superseded documents (`plan-lab.md`, `plan-rediscovery.md`) get a banner pointing here; tried README Next items
  go; wrong memory facts are corrected (human shape 13.5 / 28 / 18, not 20 / 28 / 12-15; the league refuted as tested).
- The lab stays stopped (`runs/lab/STOP`; card 020 closed), since `rl.lab start` would resume the pre-#127 recipe. Runs
  are indexed, never moved (forks read `main/seg_0460.pt`, `scr-resetcap/population_it0479.pt`); runs killed after 1-2
  iterations are indexed as unread. One evaluator per question, named in the record (`probe_matchups.py` and
  `walls_vs_humans.js` give 0.720 and 0.702 for the same walls).
- Over-broad do-not-repeat entries (learned change rate, novelty, memory, slot binding) are narrowed to what ran.
  Unlogged results (the two-turn search at 96 games, 0.583 ± 0.099) are logged first; uncommitted work waits for Evan.
