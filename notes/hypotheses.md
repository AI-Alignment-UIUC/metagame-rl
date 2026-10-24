# Hypotheses: the mechanism-level index

**What this file is.** The single index of what metagame-rl has tried, by causal node (N1-N13) and mechanism. It holds
69 families of past tests (H01-H69), the standing facts (S01-S36) and anomalies (A1-A9) they rest on, the effort map, 44
new hypotheses from this session (H70-H113; H98 tested in #153, H82's stage 1 in #156, H99 in #157, the rest untested) and the first cycle's queue. The progress log stays the full
record; this file indexes it and adds no claim the log lacks. Every family was verified against the log: verification
changed 50 of 69 statuses, and 7 of 29 refutations did not survive.

**Date and source.** 2026-10-21. Built from `notes/progress-log.md` #1-#147, plus the evening's work in #148 (search-strength
judging built; `scr-t60gate479` ended at 498) and #149 (`scr-jsearch479` stopped; JF2), the critic's review of the rebuilt
ledger, and this session's design workflow (candidates C01-C44, each reviewed, all surviving). `DATA` in a log reference
means a number recomputed from run files while the ledger was rebuilt. That number is not in the log yet.

**How to use it.** Before you propose an experiment:
1. Find its node in the table in section 4, and the node's families in section 5. Also read every family that lists the node
   as a secondary node (the node list in each family's header).
2. Read each family's verdict, then its **Do not repeat** list. A proposal that matches a recorded test on cell, lever,
   direction, dose range, start class, judge and horizon, and fixes none of its inadequacies, is a near-duplicate and is
   rejected. A new name, or "X's flags plus Y", is no difference.
3. Check section 6 for a queued hypothesis on the same mechanism. Extend it rather than open a parallel one.
4. In the experiment's record, cite the H ids it is distinct from, its 3 nearest past tests, and the factor that was never
   varied before. Untested variants listed under a family are the cheapest way into that cell.
5. A result outside every live band, or against a standing fact, gets a new A id. New families and hypotheses take the
   next free numbers (H119 and C50 are next; H118/C49 soft search targets, #169; H114/C45 the clocked pilot, #161; H115/C46 the curriculum, #163; H116/C47 the loop under the rule, #164; H117/C48 the curriculum under the rule, #167). The Q1 rival set (E game, I inputs, P pilot, J judge, S selection,
   X exploration, 0 other) and the grading rules (A, B, C) are defined in `notes/method.md` sections 4-5.

**Status vocabulary** (family headers read `### H27 · N6 · supported (moderate) · name`, giving id, nodes, status, then the
strength of the evidence behind the verdict: strong, moderate or weak):
- **established:** the mechanism was shown directly, more than once.
- **supported:** the claim holds on the evidence, with the caveats the verdict states.
- **partly-supported:** part of the claim holds, and the verdict names the part that is untested or contradicted.
- **adopted:** the change is in the recipe on the evidence stated. Its mechanism is not necessarily shown.
- **inconclusive:** tests ran but could not separate the explanations (power, confound or truncation).
- **weakened:** the evidence leans against the claim, short of a refutation.
- **underpowered:** the only test could not have shown the effect.
- **refuted:** refuted for the configuration the verdict and the do-not-repeat list name, never for the whole mechanism.
- **untested:** no test has run (a design only, or new in section 6).

Test outcome labels in parentheses (for example "refuted (distillation)") are the verifier's.

**Numbering of new hypotheses.** H(69+n) is candidate Cn: H70 is C01, H82 is C13, H83 is C14 and H113 is C44.

## 2. Standing facts

Each fact gives its id, confidence and log references. S01-S30 are copied exactly from the rebuilt ledger;
S31-S35 come from the evening of 2026-10-21 (#148, #149, analysis section 9). A result against a standing fact
gets an A id.

- **S01** · high · #120, #140, DATA · Since ~160 every one-pilot population holds one type, since ~300 Chansey/Snorlax walls: 11-12 of the top 12 hold both in every screen; never fewer than 53 of 99 decks in 460/479 forks.
- **S02** · high · #63, #126, #124, DATA · Error direction is constant: too few Trainers, too much Energy (main T -10.2, E +10.0 vs 13.5/28/18); only from-scratch runs err into Pokemon piles.
- **S03** · high · #140, #143, DATA · From the 479 state the relapse is reproducible: ungated forks re-form one type above 50 within 10-16 iterations; the A/A pair matches type sizes 33/19, 48/44, 74/72, 74/76.
- **S04** · high · #86, #96, #102, #113, DATA · Noise floors: distance A/A RMS 2.0-4.8; shape drift up to 10.5 cards a segment (bar 16); lab Elo sigma ~8.8 with ~40-Elo segment swings; competence bar 0.06.
- **S05** · high · #115, #147 · Verdicts follow the judge: the 360 best decks score 0.81 / 0.67 / 0.28 under main pilot / SimpleBot / pilot-v2; ten population pilots rate the walls 0.676-0.746, pilot-v2 0.264.
- **S06** · high · #137, #147 · The walls' verdict follows the walls' pilot (own/own 0.720, own/v2 0.761, v2/v2 0.237, v2/own 0.233); pilot-v2, trained with deck-out wins paid 0, never learned the stall plan.
- **S07** · high · #139, #141, #147 · The walls win long games: 0.360 at <=40 turns, 0.784 over 40; deck-out wins median 61-66 turns vs human prize wins 34-41; mostly ahead on prizes when they win by deck-out.
- **S08** · medium · #147 · One-turn search on both seats leaves walls at 0.573 [0.469, 0.677] (two-turn 0.583 +/- 0.099, unlogged); greedy with 60-turn draws 0.604; only search on both seats plus draws at 50-60 turns gives 0.44-0.46 (offline, 8 games a pair).
- **S09** · high · #139 · All wall cards are implemented as printed; minor open deviations remain; the env has no clock, only a 5,000-decision cap.
- **S10** · high · #92, #96, #116 · Competence flat at 0.43-0.48 since 160: attack-only lethals 86-94%, Trainer-first 58-61% (random 47%), PlusPower 31% (random 25%); one-turn search lifts them to 85-88% and 81%.
- **S11** · high · #116, #147 · No pilot training-signal or architecture change (16 lab cards, then anchor, value targets, challengers, league, turn limits, gate) moved competence by its bar or the walls' verdict.
- **S12** · high · #92 · Every pilot, including ones trained on the human lists, values only draw Trainers above basic Energy; search, disruption and tempo Trainers score 0.36-0.52 against Energy copies.
- **S13** · high · #75, #77, #78 · Credit reaches back (lambda 0.95: 56-75% of an option's effect); the weak links are a game-count-limited value (EV 0.15 at 80+ decisions to the end) and one-game noise (SNR 0.14-0.29).
- **S14** · high · #82 · Less sampling hurts (--explore 0.1 -116 Elo vs base-cont; --ent 0.001 fewer Trainers); ordinary PPO learns Trainer timing given more iterations.
- **S15** · high · #103, #105, #106 · Hard-target expert iteration lost 79/56/37 Elo; targets disagree with the pilot on 60-70% of probes; exact lethal targets ~1 per 1,194 probes.
- **S16** · high · #98, #114, #134 · Shared pilots specialise: own-deck strength 0.902->0.971 (160-360) while human-list strength stayed at pilot-v2's 82%; one-type-field pilots play human lists 27-45 Elo worse than pilot-v2.
- **S17** · medium · #131, #138 · A KL anchor made the pilot ~65-70 Elo better on the human lists than control, yet decks did not move; human-list practice raised them only 0.25->0.31.
- **S18** · high · #109, #115, #120, #127 · The draft head's incoming choice collapses to one card (0.05-0.3 nats vs 5.6), in its context weights; entropy bonuses cannot reopen it; a sampling floor holds draws but cost the pilot 27-33 Elo as lab cards.
- **S19** · high · #127 · Under forced moves 87-97% of moves at 448-449 were Energy-for-Energy swaps (basic Energy has no copy limit); median Energy reached 37 by 440.
- **S20** · high · #132, #134, #137 · A reset head with select, floor and group changes reaches 7.5-14 cards off the human medians in 20-30 iterations (3 replicates) but inside the wall type, and relapses to 15-20 as the head narrows.
- **S21** · medium · #140, DATA · The significance gate cuts moves 3.5x and holds distance 6-12, but accepted moves still add Pokemon and cut Trainers; Chansey+Snorlax decks rise 54->73.
- **S22** · medium · #124, DATA · Pool: 225 Pokemon / 42 Trainers / 6 basic / 4 special Energy (uniform draw 81% Pokemon); distance is U-shaped in head entropy (best at 1.5-2.5 nats).
- **S23** · high · #124, #132, #48, #51 · From scratch the recipe collapses within 5-40 iterations into Pokemon piles with 85-99% deck-outs; the main line attacks only through pilot-v2's bootstrap (field-card decks, deck-out wins 0, now banned).
- **S24** · high · #33, #119, #131, #133 · Self-play with the plain result and gamma 1 drifts toward stall (deck-outs 7%->44% in training; 35-61% in later populations); gamma 0.995 helped only briefly.
- **S25** · high · #68, #69, #141 · In the population's stall meta Energy-for-draw-Trainer swaps and draw-first forcing lose; the human lists lose to walls by slow prize races, not by drawing out (nodraw paired -0.002).
- **S26** · high · #36, #43, #47, #64 · Optimising a learned proxy harder made real decks worse; the start-of-game value ranks Energy/Trainer variants nearly in reverse; deck-score noise matches one-card effects (~1,000 games for 3 points).
- **S27** · high · #109, #112 · Shape swings by chance: forks of one state diverged to 31/8/20 and 13/27/19 within 12 iterations; adopt() imports the branch's population.
- **S28** · high · #57, #63, #125, #146 · Separate-pilot leagues keep types apart but shed Trainers (0-7); league heads sharing one pilot drift to piles then walls; exploiters get no signal or copy the walls.
- **S29** · high · #15, #42, #48 · Most results are single-seed; pilot-v2 carries a field-card prior and deck-out-0 shaping; card text uses frozen MiniLM (a language prior).
- **S30** · medium · DATA, #144, #147 · Deep-research trigger (user request): >=3 mechanistically different interventions within 2x A/A RMS of a matched control with unchanged top-12 core cards. Met now (~25 screens, ~40 branches). Open: judging decks without a co-adapted judge, diversity against one shared evaluator, the historical clock, soft-target search distillation.
- **S31** · high · #148, #149 · **Search-strength judging is still untested at adequate power.** `scr-jsearch479` (STOP at
  20:40, ended after 498) could not test it by design. `rl/metagame.py judged()` with `--judge-score min`, prior 4 and
  z 1.5 keeps a deck at its greedy mean unless it has dozens of searched games. A wall at greedy 0.72 over 30 games and
  searched 0.57 keeps 0.72 with 2 searched games (shrunk mean 0.67, bar 0.836), and still 0.72 with 10 (bar about 0.79). A
  minimum never raises a deck. Over 480-498 the searched games moved 50-54% of their decisions off the pilot's top option
  but changed 0-2 `--select` choices an iteration, 6 in all, against 15.5 when their results are redrawn at the greedy rate.
  There were 2.02 searched games a candidate. The trajectory tracked `scr-t60gate479`: distance 10.5, 9.3, 8.5, 8.0, 6.3
  against 10.3, 9.8, 7.0, 7.8. Decks holding both Chansey and Snorlax went from 53 of 99 at 479 to 53, 66, 76 and 89 at 484,
  489, 494 and 498, against 53, 58, 70 and 80 in `scr-t60gate479`.
- **S32** · high (code read) · #71, #116, analysis section 9 · **The attached-Energy count bug is live.** In
  `rl/token_model.py:367`, with `slot_bind` off (the current pilot), the ordered count features read every token's raw aux.
  An ENERGY token's aux is slot × 8 + copies, so 2 Energy on slot 5 reads as 42, and on slot 0 as 2. Only slot binding used
  the corrected count, and it was judged neutral on strength (#116).
- **S33** · high · #72, #73, #74, analysis section 9 · **The pilot sees both decklists.** It gets OPP_DECKLIST tokens for the
  opponent's full list and MY_UNSEEN tokens for its own unseen cards (`env/tokens.js`), information a 2000 player lacked.
  The only test that touched this was a 40-iteration from-scratch no-deck screen (#73-#74), which hid both lists, judged
  against SimpleBot.
- **S34** · high · #127, analysis section 9 (critic) · **Clutter that can cause repeats.** The lab was resumable, with no STOP
  file and card 020 'running'. `rl.lab start` would resume the pre-#127 forced-swap recipe (`runs/lab/STOP` has since been
  written, per the plan). The argparse defaults differ from the adopted recipe: swaps 3 vs 6, draft margin 0.5 vs 0, lr
  1e-4 vs 2e-4, draft-lr 1e-3 vs 3e-4, epochs 3 vs 2, shaping 0 vs 0.1. So a hand-launched run silently uses pre-adoption
  settings. `notes/scripts/screen.py` builds every screen on the lab's pre-#127 main_args plus stacked flags. 25 of 27
  screens fork from two wall states (main 460, `scr-resetcap` 479), so they test escape, not prevention. Plan documents
  are stale. The work since #127 is uncommitted (needs Evan).
- **S35** · medium (32 games a pair) · #149 · **JF2: within the human field the trained judges reproduce its structure.**
  The 24 × 24 human-list matrices were played greedy, untimed, 32 games a pair (`runs/probe/jf2_human24_v2.json`,
  `jf2_human24_resetcap499.json`; 8,832 games each, 0 errors). The judges' logit equilibria against the real field
  (Wigglytuff 0.417, Haymaker 0.292):
  - pilot-v2: TV 0.103 / 0.143 / 0.165 / 0.265 / 0.395 at lambda 5 / 10 / 20 / 40 / 80; Wigglytuff and Haymaker together
    0.69-0.90.
  - the population pilot (`scr-resetcap` 499): TV 0.098-0.250; the two archetypes together 0.71-0.84.
  - SimpleBot (#17's matrix): TV 0.148-0.533; the two together 0.33-0.58, Sponge-led.

  The Nash solution is unstable at 32 games a pair. Its bootstrap median TV is 0.458 [0.249, 0.708] for pilot-v2, 0.374
  [0.250, 0.612] for the population pilot and 0.500 [0.458, 0.671] for SimpleBot. Pairwise win rates correlate 0.64
  between the two pilots, and 0.42-0.54 between either pilot and SimpleBot. Deck-outs end 27% of pilot-v2's
  human-vs-human games and 35% of the population pilot's. So the judge's error is specific to invaders from outside the
  field (the walls) and to long games. It is not a non-human judge everywhere, and the pilots play the fast tempo decks
  slowly.

**Results logged in #150** (after this file was drafted; the entry has the exact numbers):
- The exact STS chain: `prizeTrace` in `notes/scripts/walls_vs_humans.js`, `sts_points()` in `walls_vs_humans_report.py`,
  and `runs/probe/sts_greedy_all24.jsonl`, whose 576 replayed games are identical to the stored rows. On set A (the
  `scr-resetcap` 499 walls) against all 24 lists, greedy, the walls' exact STS share is 0.482 / 0.515 / 0.543 / 0.547 /
  0.553 / 0.588 / 0.620 / 0.665 at T 20 / 25 / 30 / 35 / 40 / 45 / 50 / 60. #139's end-of-game proxy gives 0.641-0.675 on
  the same games (0.657 at 20, 0.641 at 40, 0.655 at 50, 0.675 at 60). The proxy is biased toward the walls: they build
  their Prize lead after the cut. The side ahead at the cut is ahead at the end in 53-82% of unfinished games.
- On the 8-list subset, traced reruns: search on the human side gives 0.536 (`sts_search_human_sub.jsonl`). Search on both
  seats gives 0.647 untimed after 166 of 192 games (`sts_search_both_sub.jsonl`, unfinished; 26 games missing), against
  0.590 for #147's run on the same 166 deals (+0.057 ± 0.042 paired; 50 of 166 results differ), so searched play does
  not replay exactly. Its exact STS share at T 20-45 is
  0.33-0.44.
- The two-turn search on both seats finished at 0.583 ± 0.099 over 96 games.
- `scr-t60gate479` died of EPIPE at 498 while running pre-judge-search code with 2 workers, so it was not a concurrent
  control.

- **S36** · high (3 df) · #153 · **Seed noise of the gated recipe at 479.** Three seeds of `scr-gate479`'s recipe (reseeds
  2, 3, 4) pooled with the ungated pair (`scr-ctl479`, `scr-resetcap`), window 490-499, point SD and one-sided 95% upper
  bound: top-12 distance 1.06 and 3.09 cards; largest type at the turnovers 6.8 and 19.7; wall-core (Chansey BS + Snorlax
  JU) decks 4.5 and 13.1; decks moved 0.35 and 1.02; incoming entropy 0.46 and 1.34; walls verdict under the final pilot
  (#147's probe) 0.026 and 0.076. Pairwise per-iteration distance RMS 2.45-3.28, inside S04's 2.0-4.8. An arm against
  one control needs about 2√2·SD (3.0 cards, 12.7 wall-core decks, 0.074 verdict) at the point SD. Greedy judge probes
  replay exactly (`gate479_rerun.json`).

## 3. Anomalies

Observations that no family explains. Each one is a standing target for a hypothesis.

- **A1** · #98, #105, DATA · Snorlax entered with the deck-free pilot: the deck-blind branch reached 88 Chansey+Snorlax decks by 249 (main 20 at 240); main's Snorlax decks went 21-32 -> 85-92 after adopting it at 290. *Why unexplained:* No family predicts an architecture selecting a card; architecture and fork luck confounded.
- **A2** · #139, #141 · Haymaker lists, whose Fighting attackers hit both walls for Weakness, score 0.35 vs the walls greedy; walls still 0.54 vs Haymaker with human-side search. *Why unexplained:* Weakness matchup never traced (8 games a pair).
- **A3** · #126 · 400-439: the main type added ~9 random-type basic Energy and dropped draw Trainers, yet deck-outs fell 59%->13%. *Why unexplained:* The ratchet explains Energy, not the weaker stall.
- **A4** · #131, #134 · After 20 iterations practising the human lists the pilot still played them 44 Elo worse than pilot-v2, which never saw them. *Why unexplained:* No family predicts practice failing to beat a non-practising pilot.
- **A5** · #104, #112 · The main line moved 42.5->12.5 (240-289) with no credited change; the lr2 fork kept 27 Trainers while its sibling fell to 8. *Why unexplained:* H42 describes the swing; nothing predicts which forks hold.
- **A6** · #88 · The auxiliary-heads branch had 62-69 games an iteration cut at the cap vs 7-45 on main. *Why unexplained:* Never investigated; possibly a new cycle.
- **A7** · #50 · psearch beats its own greedy pilot 65.4% but gains nothing vs SimpleBot. *Why unexplained:* Untested against an independent pilot.
- **A8** · #63, #137 · In result #2 the deck explained ~70% of cross-play strength; for the walls the pilot decides (0.72 vs 0.24). *Why unexplained:* No test separates pilot-dependent from deck-dependent decks.
- **A9** · #145, DATA · --lam-value 1 made the shape worse than control beyond A/A with value loss 0.572 vs ~0.09. *Why unexplained:* Mechanism untested.

## 4. Effort by node

The table gives the critic's count of test rows (214 in all) and its refuted and open counts per node. It adds each node's
families with their current status, and the critic's main gap. N4's 18 rows include the pending `scr-jsearch479` row.

| Node | Rows | Refuted / open (critic) | Families (first node), status | Main gap (critic) |
|---|---|---|---|---|
| N1 Game definition | 16 | 2 / 1 | H01 est · H02 part · H03 part · H04 ref | The STS round rule (Prize tiebreak at time) has never been trained. Post-fix capped games and draw-seeking were never traced. The human lists' cards were never audited. #139's label is unfixed. Turns per STS round needs outside evidence |
| N2 Pilot tactical competence | 29 | 4 / 3 | H05 part · H06 sup · H07 part · H09 ref · H10 ref · H11 ref · H12 untested · H13 adopt · H14 weak | Largest node. Most rows are one-segment, Elo-gated forks from 79-320. Only play-time search moved competence past 0.06. Open: EI v4, psearch on the Trainer panel, a whole-turn policy |
| N3 Pilot generality | 12 | 2 / 0 | H15 sup · H16 ref · H17 ref | All tests are sibling forks of one lineage on one seed. Untested: a separate best-response network against frozen walls. `scr-practice1k` was never read |
| N4 The judge | 18 | 2 / 3 | H18 sup · H19 weak · H20 weak · H21 ref · H22 weak · H23 inc | It is the named driver (F2), yet its rows are mostly offline probes. Only two judge changes ran in training (`scr-judge2`; `scr-jsearch479`, inert). No judge that is both strong and not co-adapted has ever been in the loop |
| N5 Selection statistics | 10 | 2 / 0 | H24 est · H25 part · H26 ref | The gate is confounded with 1 vs 3 candidates and 20.2 vs 10.1 games a candidate. z was tried at one value. Accepted moves were never re-scored on fresh games |
| N6 Draft operator | 27 | 1 / 4 | H27 sup · H28 adopt · H29 adopt · H30 part · H31 ref · H32 weak · H33 inc · H34 weak · H35 untested | Five families (15 rows) treat incoming entropy, yet accepted moves diverge from proposed ones (#140). Never tested: the cut choice, kind-balanced proposals, the optimizer, a learned change rate under select, group changes apart from the floor, the head's input after 290 |
| N7 Population ecosystem | 21 | 2 / 4 | H36 inc · H37 weak · H38 inc · H39 ref · H40 inc · H41 weak · H42 sup | Every diversity mechanism ran under the one walls-biased judge. The soft cap was overrun (72-76 decks against 49.5). The Pokémon-overlap descriptor misses walls |
| N8 Coupling and timescales | 6 | 1 / 1 | H43 inc · H44 ref | Seasons ran only in the pre-select loop. Never run: per-candidate adaptation before judging, seasons with `--select` |
| N9 Initialisation and bootstrap | 7 | 1 / 1 | H45 part · H46 ref | One substantive from-scratch run (40 of 160 iterations, one seed). Never run: the kind-balanced prior × plain-result pilot 2×2, a pilot-first warm-up |
| N10 Value and credit | 19 | 5 / 2 | H08 ref · H47 weak · H48 inc · H49 ref · H50 under · H51 part · H52 part · H53 weak · H54 weak | Most rows are single forks on A4-era or pre-290 pilots. Credit was never probed in 60+ turn games or at prompts. Untested: margin as the terminal reward, a judge-side length discount, per-player final counters |
| N11 Pilot architecture | 17 | 0 / 4 | H55 adopt · H56 inc · H57 part · H58 inc · H59 inc · H60 adopt | Every test was a single fork, most stopped at the first Elo gate. The s1 puzzles ran with history 0. The attached-Energy count bug is unfixed outside slot binding. A1 is unexplained |
| N12 Measurement | 20 | 3 / 2 | H61 part · H62 weak · H63 ref · H64 ref · H65 inc · H66 part | Each decision yardstick proved shape-blind or judge-biased. The noise bars come from 2 A/A forks at 160 and were not recalibrated after 4 adoptions. s1 has no passing positive control |
| N13 Proxy deck objectives | 12 | 1 / 2 | H67 ref · H68 inc · H69 inc | All 12 rows predate #64 and use deleted builders. The draft head still reads decks as a pre-game state (#65), never re-checked. The overoptimisation curve was never measured |

Legend: est established, sup supported, part partly-supported, adopt adopted, inc inconclusive, weak weakened, under
underpowered, ref refuted.

**The research program's own mode collapse.** Effort piled onto levers downstream of the judge. Of 214 test rows, 134 (63%)
fall on six nodes: N2 29, N6 27, N7 21, N12 20, N10 19, N4 18. The node the record names as the driver (N4, F2) got only
two interventions in the loop. One was `scr-judge2`, with pilot-v2 on half the games and no gate. The other was
`scr-jsearch479`: 2.02 searched games a candidate, 6 selection flips against 15.5 from redraw noise, stopped. Three
clusters of near-identical tests account for much of the rest:
- 65 pilot-side rows (N2, N10, N11). #116 counted 16 cards that never moved competence past its bar. After #137 showed
  that the verdict follows the walls' pilot, six more pilot-training changes still ran expecting the decks to move.
- 20 rows on the draft head's entropy (H30-H34, league and exploiter heads), although #140 showed that accepted moves
  diverge from proposed ones.
- 13 or more population pilots re-measured as judges, at 0.68-0.83 each time.

The experiments were collapsed too. 25 of 27 screens forked from two states that were already mostly walls: 14 from main
460 on seed 1 (all 8 reset screens among them) and 11 from `scr-resetcap` 479 on reseed 2. So they tested escape, not
prevention, and their replicates are correlated. 8 screens ran 8 iterations or fewer. Under-tested areas:
- N8 (6 rows), N9 (7 rows) and N13 (12 rows, all on builders deleted at #64);
- the game's payoff under N1: the Prize-tiebreak clock was never trained.

This is the model's own failure one level up: local edits stacked on an incumbent recipe, selected by a noisy short-horizon
score, with no niching and no archive. The archive in this file, the do-not-repeat lists, the coverage gaps below and the
floor of `notes/method.md` section 8 are the remedy. Outside research is the bottleneck today for only one question that no
run can answer: how many engine turns a 20-minute STS 2000 round allowed, and how stall decks fared in 2000 (H71).

**Coverage gaps the critic named, and what now covers them:**

| Gap (node) | Covered by |
|---|---|
| The outgoing (cut) choice: no family covers it, and accepted moves cut 0.2-1.9 Trainers each (N6) | H93 (first test of the cut), H111 |
| Who a deck is scored against: population-mean fitness against a field that is 73-79% walls (N4/N5) | H89 (panel arm), H107 (arm P), H112, H96 |
| Prompt and sub-decisions inside Trainers, which qprobe skips (N2/N10) | H80 |
| How the pilot reads Energy quantity: the live count bug (N11) | H77, H76 (slot-bind pair) |
| Target validity: is the human meta optimal only under the 2000 clock? (N1/N12, outside research) | H71, H82, H85, H100 |
| Draw-seeking under capped or turn-limited games (N1/N10) | H83 |
| Judge-variance penalty, from anomaly A8 (N4/N7) | H90 |
| Pilot-representation changes silently re-route the head, from A1 (N11/N6) | H76 (encoder pair), H94 (H-encoder rival) |
| Per-archetype trace of the walls' edge, from A2 (N2/N4) | H87 (per-archetype readout) |
| Training regime vs exposure for general skill, from A4 (N3/N10) | H86, H91 |
| Per-card credit inside a 6-change draw (N6/N10) | H95, H84 (per-card advantage sums) |
| The meta-level solution concept (N7/N5) | H96, H85 |
| The draft head inherits the opening-value Energy bias (N13/N6) | not queued: H35's reading-ablation variants |
| Open decklists (N1/N2) | H78 |

**Repeat clusters the critic found** (each is in the matching family's do-not-repeat list):
- The walls judged by a population-grown pilot against the 24 lists: about 13 pilots, 0.68-0.83 each (#127, #131, #133,
  #137, #147).
- Changing what the shared pilot trains on while the same co-adapted pilot judges: wide practice, human-list practice, KL
  anchor, varied field, challenger practice, Monte Carlo value targets, gamma 0.995 (#130-#147).
- A reset head with select, floor and group changes, forked from main 460 on seed 1: 8 screens (#130-#138).
- Near-uniform draws over a pool that is 225 of 277 Pokémon, drifting into Pokémon piles, seen six ways without the
  kind-balanced control (#63, #120-#132).
- Hard one-hot expert-iteration targets from a few re-dealt lines, scored by the live pilot's own value (#103, #105, #106).
- A frozen human-free pilot trained with deck-out wins 0 as judge or drafter (#42-#47, #131, #132/#134).
- Training the shared pilot from the challenger side (#127/#131/#134, #141, #142/#145, #143/#146).
- One-turn psearch k4 dets4 on resetcap 499's three walls and #139's 192 deals (#139, #145-#147).
- Accept a deck change only if real games say it is better, with no significance gate, built four times (#43, #56-#63,
  #127-#140).
- The soft type cap 0.5 with wide turnover, carried in 17 of 27 screens and never ablated (#129-#146).
- An entropy bonus of 0.05 on a reset head, inherited by `scr-anchor` from its control (#134-#138).
- Plain game-length penalties under a greedy or sampled population judge (#131-#133, #142/#143, `scr-t60gate479`, #147).

## 5. Families by node

The 69 verified families, grouped by first node. Each family gives its mechanism, verdict, tests (log, result,
outcome), its do-not-repeat configurations, and its untested variants with why each is distinct and what it costs.
A last line lists the new hypotheses of section 6 that test it or must cite it.

Nodes: N1 Game definition (H01, H02, H03, H04); N2 Pilot tactical competence (H05, H06, H07, H09, H10, H11, H12, H13, H14); N3 Pilot generality across deck types (H15, H16, H17); N4 The judge (H18, H19, H20, H21, H22, H23); N5 Selection statistics (H24, H25, H26); N6 Draft operator (H27, H28, H29, H30, H31, H32, H33, H34, H35); N7 Population ecosystem (H36, H37, H38, H39, H40, H41, H42); N8 Coupling and timescales between levels (H43, H44); N9 Initialisation and bootstrap (H45, H46); N10 Value and credit learning (H08, H47, H48, H49, H50, H51, H52, H53, H54); N11 Pilot architecture (H55, H56, H57, H58, H59, H60); N12 Measurement (H61, H62, H63, H64, H65, H66); N13 Proxy deck objectives (H67, H68, H69).

## N1 · Game definition

### H01 · N1 · established (strong) · Free cycles in the action space are exploited

- **Mechanism:** With end-only reward and gamma 1, a capped or drawn game pays 0, which beats a loss, so a losing policy learns any free no-op cycle that reaches the cap (stated directly only in #58).
- **Verdict:** Established: free no-op cycles were found and exploited (#12, #14, #20, #58, #62), and each fix restored normal game lengths. Not shown: that the fixes closed the path. A 250-decision per-turn cap still allows a 5,000-cap draw after about 20 cycling own turns, post-fix capped games (0.16-0.67%) were never traced, and the steady rise of --max-turns draws in #142 was never checked for draw-seeking.
- **Tests:**
  - #12: Heuristic looped on Ditto Transform use-Power -> cancel to the 5,000-step cap; dead-end rule dropped 3,721 dead-end Powers in 800 games (adopted (first instance))
  - #14: A3 run 1: 189->713 decisions/episode by it 74, 42% cancels; 2,627 of 2,714 cancel prompts pure undo; removed (adopted)
  - #20: Metronome/Rain Dance/Transform cycles: cut games 44/52 -> 0; A4.1 field 88.0->88.5%, mirror 89.25->89.6% (adopted)
  - #58: Tentacool Cowardice 'no' cycle: 2,400 'no' a game; 50 of 889 games cut, 33 in agent 4's 130 games; found when losing (adopted)
  - #62: Shuffle-hidden Dark Dragonair cycle: 25% greedy vs 0.5% training games capped; 23-28 of 96 greedy tournament games; MAX_TURN_STEPS 250 added (adopted)
  - #63, #69: Post-fix capped games 0.16-0.26% (#63) and 2,012 of 300,000 (0.67%, #69); never traced with trace_loop.js (open)
  - #142: --max-turns 40 (draw pays pilot 0): games at limit 43%->94% (1,856 of 2,000 at 492); pass/attack rates by side never checked (unchecked confound)
- **Do not repeat:**
  - Using pre-fix results as clean: A3 run 1, A4.1 original exit scores (field 88.0%, mirror 89.25%), the first a4-tok run (stopped at it 24)
  - league-3 agent 4 (e1.1) pre-reset network, league-3 rounds 13-14 games, tourn-3-prefix and tourn-3-loopbug results
  - Training with a --max-turns draw paying the pilot more than a loss without logging the capped/time share by losing side and tracing a sample (#142 scr-turns40)
  - Treating pilot-v2 (#48), coevo-1 (#52-53) or league-3 rounds 0-12 as verified loop-free without a trace (trained before the #58/#62 fixes)
- **Untested variants:**
  - Progress invariant in the fuzz/runtime: many decisions with no zone change, or a repeated state within a turn (#58 Next, never built). *Distinct:* A detector: catches shuffle-hidden and sub-cap cycles the replay-to-same-state filter misses (#62). *Cost:* low
  - Capped game scored as a loss for the pilot. *Distinct:* Removes the incentive rather than detecting cycles; legitimate games rarely reach 5,000 decisions (~70-100 per player). *Cost:* low
  - --max-turns draw paid as a loss to both pilots, or decided by prize margin (STS round rule) in training. *Distinct:* Separates draw-seeking from the deck-shift explanation of #142's rise to 94% draws. *Cost:* low-medium (1 screen)
  - Game-level budget for capped turns (N turns hitting MAX_TURN_STEPS = loss) or a smaller MAX_TURN_STEPS. *Distinct:* Closes the 250 x ~20-turn path to the 5,000 cap that the walls' 43-80-turn games can reach. *Cost:* low
  - Trace a sample of post-fix capped games (#63, #69) and today's screens' capped/time games with trace_loop.js --greedy, logging per-side pass/attack rates. *Distinct:* Diagnostic: tells residual cycles and draw-seeking apart from legitimate long games. *Cost:* low
- **New hypotheses (section 6):** H70, H83

### H02 · N1, N11 · partly-supported (moderate) · Engine or interface faults explain results (incl. the walls)

- **Mechanism:** Card bugs, hangs, silent option or token truncation, seed errors or free cycles could create or hide strategic value and so bias which decks win.
- **Verdict:** Refuted for the walls' own cards and end rules: #139's adversarial audit found them as printed, with only minor deviations. The general mechanism is real: earlier engine and interface faults (#14, #20, #43, #58, #62, #68) did create or hide strategic value, and their fixes changed outcomes. Still open: the human lists' cards were never audited adversarially, the minor deviations were never fixed and measured (including the ending label, which touches pilot-v2's training), and cap hits in walls games are unmeasured.
- **Tests:**
  - #1, #9: 24/24 human lists build; specs 541->686, 68/68 interactions, rulings 23/23 after T18 fix; 1,926 card-data checks, 1 cosmetic mismatch (passed (non-adversarial))
  - #5, #11, #14: Enumerator vs oracle, 10,000 games: 0 mismatches, missing, invalid or engine errors; re-verified on 991,580 main-phase decisions (passed)
  - #34: Seeds above 2^53 fixed; over 48 options handled by offering only the first 48 (itself silent truncation); 31,680 builder-panel games, 0 errors (partial fix)
  - #25, #68: Max 41 options / 118 tokens over 397,663 decisions (#25); max 39 options on meta-99 at it 79 (#68); option truncation inert (refuted (option channel))
  - #68: Bounds raised to 128 options / 256 tokens, overflow now an engine error; 11 decisions (0.03%) had exceeded the old 128-token bound silently (adopted)
  - #44-#46: Coin-flip hang found in Worlds 2005; latent in 2000 only on full pool (Geodude FO); flip cap 32; 300 seeded traces identical (adopted)
  - #52, #53: Two full-pool crash bugs (16 of 360 decks); 3,660 games 0 errors after; Special Energy never generated before; with DCE the meta still collapsed (adopted; no effect on collapse)
  - #14, #20, #58, #62: Free no-op cycles created stalling value; fixes changed outcomes (Viray Rain Dance 67%/61% -> 71%/72%, cut-offs 44/52 -> 0) (supported (mechanism real))
  - #43, #46: Value-scorer deals depended on batch position (SD 0.018-0.026); shadowed variable made head propose 8 decks; count embedding left at random init (supported (harness faults))
  - #63: Venomoth JU Shift lacked a once-per-turn marker and changed the wrong Pokémon's type; fixed (adopted)
  - #69: 300,000 games: 2 engine errors, 2,012 cut off (0.67%) (residual rate)
  - #92: PlusPower, Gust of Wind, Computer Search engine behaviour and pilot inputs (HP, damage, attack damage, tools) checked correct (passed)
  - #139: Adversarial audit of every walls card and end rule: all as printed; minor: 2003 Confusion, Maintenance order, Thick Skinned edge, simultaneous win = draw, ending label (refuted (walls))
  - #139, #141: ONNX parity max logit diff 8.1e-6, argmax agreement 1.000 on 200 states; pilot sees both deck sizes (refuted (observation fault))
- **Do not repeat:**
  - Re-auditing the walls' cards and end rules against the print (#139)
  - Re-counting max options on human or meta-99 decks (#25, #68)
  - Re-auditing 'once during your turn' Powers in the 2000 sets (#62)
  - Re-verifying the enumerator against the oracle on the 2000 field (#5, #11, #14)
  - Re-checking PlusPower, Gust of Wind and Computer Search code and pilot inputs (#92)
  - Re-checking ONNX/PyTorch pilot parity (#139) or whether the pilot sees deck sizes (#141)
  - Re-testing the flip cap or trace equality on seeded 2000 games (#46, #62)
  - Re-running the full-pool crash fuzz without new cards (#52, #58, #62)
- **Untested variants:**
  - Fix #139's minor deviations and rerun the walls probe; prioritise the ending-label fix with pilot-v2 re-rating or retraining. *Distinct:* Effect never measured; the ending label paid 0 for some no-Pokémon wins in pilot-v2's --deckout-win 0 training, and pilot-v2 is the reference judge. *Cost:* low
  - Adversarial audit of the human lists' cards (Do the Wave, Item Finder, Scoop Up, Lass, Invisible Wall, Rain Dance, Hitmonchan, Scyther, Electabuzz, Articuno, plus the #20 Metronome deviation). *Distinct:* An under-powered human-list card would make the walls look good with no wall card wrong; #139 was walls-only, #92 covered 3 Trainers. *Cost:* low
  - Measure how often walls games hit MAX_TURN_STEPS 250 or the 5,000-decision cap, and how those games are scored. *Distinct:* Both caps were added for loop bugs and never checked against stall archetypes that win long games. *Cost:* low
- **New hypotheses (section 6):** H70, H75

### H03 · N1, N4 · partly-supported (weak) · The walls' edge is the long, clockless game

- **Mechanism:** Without a clock, decks that survive past about 60 turns win by deck-out, while the human lists were built for 20-minute rounds decided by Prizes.
- **Verdict:** Shown, offline and under the walls' own population pilot: the walls win long games (0.360 at 40 turns or fewer vs 0.784 over 40; deck-out median 61-66 turns), and only one-turn search on both seats together with draws at 50-60 turns brings them to 0.44-0.46 (192 games; the interval includes 0.5). Not shown: that a clock removes the edge (greedy Prize-tiebreak rescoring still gives 0.625-0.658, and the walls lead on Prizes in 109 of 148 deck-outs), that it holds under a non-population pilot (pilot-v2 rates them 0.26 with no clock), or that it holds in training (limits of 40/70/120 and gamma 0.995 all failed).
- **Tests:**
  - #141 (on #139's 576 deals): Greedy walls 0.360 at <=40 turns (n 111), 0.784 over 40 (n 465); correlational, open to selection (supported (correlational))
  - #139: Walls' deck-out wins median 61 turns (range 43-80); human lists' prize wins 34-41 turns (supported)
  - #139: STS round rule at 40-60 cuts: greedy 0.625-0.658 (all 24 lists 0.641-0.675); human-side search 0.400/0.426/0.486; prize counts approximated (mixed)
  - #141: At walls' deck-out wins: ahead on Prizes 109, even 21, behind 18 of 148 (against under greedy play)
  - #141: nodraw:15 on human side: 0.701 vs 0.702, paired -0.002, 571 of 576 games identical; human lists lose prize races (against draw-out explanation)
  - #147: Draws at T 40/50/60/70/100: greedy .469/.500/.604/.654/.703; human-side search .401/.417/.464/.510/.578; both .435/.440/.458/.500/.573; 192 games (partly supported, underpowered)
  - #147: Both-seat search 0.573 [0.469, 0.677]; 0.222 at <=40 vs 0.680 over 40; deck-out median 66; 83 of 110 wins by deck-out (supported (correlational))
  - #145-#146: One-turn search both seats, 152 games: walls 0.592 vs greedy 0.734, human-side only 0.572 (does not flip)
  - #147: Two-turn search both seats, 49 games: 0.571 vs one-turn 0.531 on same deals (underpowered)
  - #140, #142-#143: In-training plain-draw limits from 479: at 40 draws 43%->94%; at 70/120 largest type 42/51 vs control 74, relapse (refuted (training lever))
  - #132-#133: gamma 0.995: deck-outs 13-19% then 30-44% by 490-498; distance 17.8-21.2; from scratch still Pokémon piles (refuted)
  - #32-#33, #48, #51: --deckout-win 0: deck-outs 39%->27%; pilot-v2 trained so rates walls 0.26; ruled game-specific (#51) (supported (mechanism), disallowed)
  - #52, #124, #126: Co-evolution found Chansey stall, deck-outs up to 41%; scratch 99% deck-outs; main line deck-outs 59%->13% while Energy rose to 36.5 (mixed)
- **Do not repeat:**
  - Offline rescoring of #139/#147's games (scr-resetcap 499 pilot) at draw or STS cuts of 30-100 turns
  - In-training plain-draw turn limits at 40, 70 and 120 turns from 479 with scr-ctl479's recipe (#140, #142-#143)
  - Greedy judge with a 60-turn draw limit (#147: walls 0.604)
  - --gamma 0.995 on the screens' recipe from 460 and from scratch (#132-#133)
  - One-turn psearch (k 4, dets 4) on both seats or the human seat only, walls vs one list per archetype on #139's deals (#139, #145-#147)
  - nodraw:15 diagnosis of human-side draw cards (#141)
  - Per-pilot judge probes of the 3 walls vs 24 lists for today's screen pilots (#147)
  - --deckout-win 0 in training (#33/#48; ruled game-specific #51)
- **Untested variants:**
  - [outside research] Engine turns per 20-minute STS 2000 round, extra turns at time, and whether players avoided stall decks. *Distinct:* A calibration: decides whether the only favourable condition (a cut at 50-60 turns) is faithful; the round rule itself is already sourced (#139). *Cost:* deep research
  - STS round rule (Prize tiebreak) in training. *Distinct:* Keeps the prize margin as the end score at the limit, unlike the plain draws swept; record predicts a weak effect under greedy play. *Cost:* low; Evan's call
  - Search-strength judging + --max-turns 60 + significance gate in training from 479 (#147 Next; launched as scr-jsearch479 per #148, no result logged). *Distinct:* The only in-training test of the family's actual prediction (clock plus competent play). *Cost:* 1 screen
  - Game-length split and draw-at-T rescoring of the walls under pilot-v2 or another non-population pilot. *Distinct:* Separates the long-game edge from judge co-adaptation (F2). *Cost:* low
  - More games per pair for the both-seat search rescoring (e.g. 32 a pair over all 24 lists). *Distinct:* Tells 0.44-0.46 at T 50-60 apart from 0.5. *Cost:* low-medium
  - Deck-out-avoidance puzzles (evaluation only). *Distinct:* Measures pilot deck management; nodraw:15 already suggests low value; as a training input it would break Rule 1. *Cost:* low
- **New hypotheses (section 6):** H70, H71, H82, H102

### H04 · N1, N5 · refuted (moderate) · Plain turn-limit draws in training stop the collapse

**Evan:** his idea (rule 4: tried first and fully).

- **Mechanism:** Ending long games as 0.5 draws removes the walls' deck-out payoff.
- **Verdict:** Refuted as a standalone lever from the collapsed 479 state, on scr-ctl479's ungated recipe. At a 40-turn limit, draws swamped the signal and 96 of 99 decks became Chansey+Snorlax by 492; at 70 and 120 turns the field relapsed like the control. #147's offline rescoring confirms that a greedy judge still rates the walls 0.500-0.703 at draws of T 50-100. Not tested: a 45-55-turn limit, a limit from a pre-collapse state, a Prize-tiebreak limit, or a limit on judging games only; the 60-turn arm was confounded with greedy judging and died at 498.
- **Tests:**
  - #140: Smoke runs/smoke/maxturns: 67 and 87 of 160 games ended by time at limit 40 (infrastructure)
  - #142: scr-turns40: at limit 43%->94% (1,856 of 2,000 at 492); median 19/26/15; Energy 15-17, distance 3.3 at 486; Chansey+Snorlax decks 53->96 of 99 (refuted (type); degenerate)
  - #143: scr-turns70/120: largest type 42 and 51 by 494 vs control 74; offline 57/53 vs ctl479 59; C+S 92/86 vs 79; distance 14-17 (refuted)
  - unlogged (scr-t60gate479): max-turns 60 + judge-explore 0 + gate: distance ~7.2 vs gate 9.2 (490-498); type 41 vs 23; C+S 53->80 vs 73; died at 498 (EPIPE) (inconclusive (confounded, crashed))
  - #147: Offline draws at T 40/50/60/70/100: greedy .469/.500/.604/.654/.703; search both seats .435/.440/.458/.500/.573 (refuted (standalone))
  - #147: scr-turns70 pilot as judge (without the limit) rates walls 0.735 (training under limit did not change judge)
  - #139: STS round-rule rescoring at 30-60 cuts: greedy 0.625-0.675; human-side search 0.40-0.49 (cross-reference (Prize-tiebreak payoff))
- **Do not repeat:**
  - --max-turns 40 in training (#142 scr-turns40: draws take over within ~10 iterations)
  - --max-turns 70 and 120 from 479 with scr-ctl479's ungated recipe (#143)
  - Comparing a --judge-explore 0 + --max-turns 60 + gate arm from 479 against scr-gate479 (sampled judging) as its control
  - Offline rescoring of greedy or psearch games with draws at T 40-100 (#147) or STS cuts at 30-60 (#139) with the same pilots
- **Untested variants:**
  - Turn limit on judging games only. *Distinct:* Separates selection from pilot training; #147 predicts greedy judge ~0.50-0.60 at T 50-60, so likely negative without search. *Cost:* 1 screen; low priority
  - --max-turns 45-55 in training. *Distinct:* Only window where #147 puts the greedy judge near parity (0.500 at T 50) while most games are not draws. *Cost:* 1 screen
  - Turn limit from a pre-collapse state (460 with the gate, #140 Next) or from scratch. *Distinct:* Tests prevention rather than escape; 479 starts with 53 of 99 decks as walls. *Cost:* 1 screen
  - Prize-tiebreak limit (STS round rule) in training. *Distinct:* A slow prize lead pays 2/3 rather than 0.5, rewarding the prize race. *Cost:* 1 screen; Evan's call
  - --max-turns 60 + greedy judge + gate vs a matched greedy-judge + gate control, run to completion. *Distinct:* The 60-turn arm was confounded with greedy judging and crashed at 498. *Cost:* 2 screens
  - Probe a limit-trained pilot (scr-turns70, scr-t60gate479) as judge under its own limit. *Distinct:* #147 probed scr-turns70 only without the limit. *Cost:* low
  - [outside research] Engine turns per 20-minute STS round. *Distinct:* Without it any training limit is a free parameter. *Cost:* deep research
- **New hypotheses (section 6):** H70, H71, H83, H84, H100, H102, H103

## N2 · Pilot tactical competence

### H05 · N2 · partly-supported (moderate) · Play-time lookahead fixes in-turn tactics

- **Mechanism:** The pilot ranks the winning setup move in its top-k but cannot see that it wins; short determinized lookahead recovers it when the payoff is terminal within the turn.
- **Verdict:** Shown: one-turn determinized play-time search finds in-turn lethals that the greedy pilot misses (on 408 puzzles, Trainer-first 59.8->84.5/87.6% and PlusPower 31.3->81.3%), and it cuts the walls' score in non-deck-out games (0.648->0.277). Not shown: transfer to outside opponents (no gain against SimpleBot at dets 4) or a flipped verdict on the walls (both seats 0.573-0.592; deck-outs rise). Every match test searched over the same network that played the opponent, two-turn search is underpowered at 49 games, and all three distillations of the search lost Elo.
- **Tests:**
  - #13: Flat MC over the heuristic: 2-turn horizon 25.0% +/- 21.2 (16 games); to-end rollouts 37.5% +/- 16.8 (32 games) (underpowered (heuristic, not pilot))
  - #49: Sampled best-of-9 replay vs SimpleBot, 960 deals: greedy 82.9%, best of 9 97.6%, 23 deals never won; ceiling overstated (indirect)
  - #50: psearch k4 dets4: 65.4% +/- 6.0 vs own greedy; vs SimpleBot target decks 71.7 vs 74.4 greedy, all 24 82.5 vs 81.7 (mixed; transfer failed)
  - #92: Greedy pilots solve Trainer-first lethals barely above random and PlusPower-then-attack at random's rate (motivating diagnosis)
  - #96: 408 puzzles at 220: Trainer-first 59.8->84.5/87.6%; PlusPower 31.3->81.3% (16 puzzles); all 79.2->89.0/90.2% (supported (in-turn lethals))
  - #139: Human-side psearch vs greedy walls: walls 0.706->0.578; non-deck-out 0.648->0.277; deck-outs 31%->51%; 8 games a pair (mixed)
  - #145-#146: Both seats, 152 games: walls 0.592 vs greedy 0.734, human-side only 0.572 (verdict not flipped)
  - #147: Both seats, 192 games: 0.573 [0.469, 0.677] vs greedy 0.706; two-turn 0.571 vs one-turn 0.531 (49 games); with draws at 50-60: 0.44-0.46 (not flipped; two-turn underpowered)
  - #103: Distilled one-turn search, weight 1.0, 8 options, 4 lines: -78.6 Elo; search favours immediate plays (refuted (distillation))
  - #105: Weight 0.3, 2 lines: -56.1 Elo; 570-655 of ~1,000 targets differed from the move played, noise-like (refuted (distillation))
  - #106: Two-turn targets, 4 lines, margin 0.15, weight 0.3: -36.6 Elo; lethal-only exact targets too rare (refuted (distillation))
- **Do not repeat:**
  - Flat MC over the heuristic with 4 rollouts, 2-turn or to-end (#13)
  - psearch k4 dets4 vs SimpleBot on the 24 lists (#50)
  - psearch k4/k8 on the 408 win-this-turn puzzles at the main-line pilot 220 (#96)
  - psearch k4 dets4 on the human side vs the greedy walls (scr-resetcap 499) on #139's 192 deals
  - One-turn psearch k4 dets4 on both seats judging the walls vs one list per archetype (#145-#147, 192 games)
  - Expert iteration with hard argmax targets: one-turn weight 1.0 (#103), weight 0.3 with 2 lines (#105), two-turn weight 0.3 margin 0.15 (#106)
  - Lethal-only exact search targets at random probes (#106)
- **Untested variants:**
  - psearch vs an independent pilot (pilot-scratch, #42) in both directions, dets 8. *Distinct:* Measurement control for #50's own-misplay confound. *Cost:* low
  - Search whose leaf value comes from a frozen independent pilot (e.g. pilot-v2). *Distinct:* Removes the co-adapted leaf value that #144's notes name as a main error source. *Cost:* low-medium
  - SPARTA-style gated play-time search: keep the pilot's move unless search beats it by a noise-scaled threshold, with 2-SD pruning. *Distinct:* Proposed in #144 only for expert iteration; never used at play time. *Cost:* medium
  - More determinizations/lines (dets 8-16) at one- or two-turn horizon; finish the two-turn run (49 of 96 games). *Distinct:* Attacks the 2-4-line noise; two-turn result is underpowered, not refuted. *Cost:* low-medium
  - Deck-counting or longer-horizon search that manages deck size against stall (#139 Next). *Distinct:* Targets the deck-out mechanism that one-turn search raises. *Cost:* medium
  - Binary move decomposition for determinized MCTS (Cowling, Ward & Powley). *Distinct:* Different search structure over the action sequence; in the notes, not built. *Cost:* medium
  - Information-set MCTS. *Distinct:* Weakly distinct: notes argue strategy fusion is confined to the root and noise plus the biased leaf dominate; already surveyed. *Cost:* medium
  - [outside research] Learned value combined with sound imperfect-information search in TCG/MTG agents, and deck-size management against stall. *Distinct:* Recorded gap in the notes; not covered by the first review. *Cost:* deep research
- **New hypotheses (section 6):** H72, H79, H82, H106

### H06 · N2 · supported (moderate) · Setup-before-attack sequencing deficit

- **Mechanism:** A one-action pointer policy with a weak value cannot tell apart the situations in which a setup or tempo Trainer converts into a KO, so it attacks first; credit delay is not the bottleneck.
- **Verdict:** Shown: greedy pilots solve attack-only lethals (86-94%) but Trainer-first lethals only at 58-68% (85-88% with one-turn search), and every learned pilot rates search, disrupt and tempo Trainers below basic Energy. Not shown: that weak per-move credit is the cause (#79 finds Trainer credit share about twice average, and #82's ordinary PPO improved timing), that PlusPower stays near random after 220 (later 0.438-0.5625 of 16), or that the panel's sub-0.5 values are misplay rather than the cards' mirror value.
- **Tests:**
  - #68: 600 greedy games: 20,389 of 29,723 turns ended holding a playable Bill/Oak/Computer Search; Energy->draw swaps hurt under SimpleBot too (supported)
  - #92: Puzzles at 220: attack-won 90/94/86%; Trainer-first 60/58/61% (random 47%, heuristic 62%); PlusPower 31% (random 25%); 51% of first moves win (supported)
  - #92: Panel (4 learned pilots + SimpleBot): draw 0.643-0.762; search 0.424-0.480, disrupt 0.457-0.521, tempo 0.365-0.465; SimpleBot 0.379/0.397/0.333 (supported; no reference-strength player)
  - #92: Gust then a prize: 0.7% greedy main, 4.0% main sampled, 1.9% pilot-v2, 7.7% a4-tok vs 10-12% on all turns (supported)
  - #96: One-turn search: Trainer-first 60->85-88%, PlusPower 31->81%; winning setup usually in the pilot's top 4 (supported)
  - #101-#126: Competence 0.434 (160), 0.480 (280), 0.496 (310), 0.472 (320), 0.447 (360), 0.460 (400), 0.483 (440); A/A bar 0.06 (supported (flat))
  - #101-#126: PlusPower puzzles (16): 0.5625 (280), 0.563 (310), 0.500 (320), 0.438 (360, 400), 0.500 (440) (against 'near random' after 220)
  - #75: One-step value credit share 14-36%, alignment 0.19-0.54; at lambda 0.95 share 56-75% (mixed (value is the weak link))
  - #79, #80: Credit share at Trainer decisions 0.41-0.54 vs 0.26; greedy timing gains Gust +2.12, Energy Retrieval +2.48, PlusPower +0.88 (against credit-delay cause)
  - #82: base-cont: timing gain +1.32->+0.39, play rate 0.225->0.326; --explore 0.1 -116 Elo (against credit-delay cause)
  - #99, #103: Memory: hist4 -0.016 competence, memattn -18 Elo, memgru -21 Elo (refuted (memory fix))
  - #103, #105, #106: Expert iteration -79/-56/-37 Elo (weight 1.0 gave +10 points Trainer-first); lethal-only 1 target in 1,194 probes (refuted (distillation))
  - #105, #106, #108: Lambda 1 in turn -37 Elo; lasting shaping -31 Elo; entropy 0.02 competence -0.005 (refuted (fixes))
  - #111-#116: 6/8-layer pilots, slot binding cold/warm: none of 16 pilot cards moved competence by the 0.06 bar (refuted (fixes))
  - #124: From-scratch pilot competence 0.356; Trainer-first 0.24, PlusPower 0.06 (supported)
  - #139, #146, #147: One-turn search both seats lowers walls 0.71-0.73 -> 0.57-0.59; two-turn 0.571 vs 0.531 at 49 games (supported (link to verdict))
- **Do not repeat:**
  - Re-scoring the 408 puzzles or the Trainer-value panel on already-measured checkpoints (160, 220, 280, 310, 320, 360, 400, 440)
  - Play-time one-turn psearch on the 408 puzzles at the 220 pilot (#96)
  - Expert iteration with hard argmax one-turn search targets from the pilot's own value (weights 1.0 and 0.3, 2-4 lines, horizon 1 or 2, margin 0.15; #103, #105, #106)
  - Lethal-only exact search targets at random probes (#106)
  - --lam-turn 1 and lasting/non-fading prize shaping as setup fixes (#105, #106)
  - --ent 0.02 as a Trainer-play fix (#108)
  - --explore 0.1 mostly-greedy collection (#82)
  - History tokens, attention memory, GRU memory (#99, #103)
  - 6/8-layer depth growth and slot binding as competence fixes (#111-#116)
- **Untested variants:**
  - Whole-turn plan head (macro-actions over a turn). *Distinct:* Changes the action abstraction; psearch ranks only the first move and expert iteration keeps the one-action policy; training (not only searching) a turn policy needs outside research beyond Rubin 2026. *Cost:* high; [outside research]
  - Self-Imitation Learning (game-level or within-turn on KO/prize turns). *Distinct:* Uses own realised returns, not search scores; caveats: return noise is 3-7x signal (#75) and game-level SIL would reinforce the stall plan. *Cost:* medium
  - Run psearch (k 4, dets 4) on the Trainer-value panel (#92 Next). *Distinct:* Separates pilot misplay from the cards' real mirror-match value for search/disrupt/tempo. *Cost:* low
  - Expert iteration v4 with soft, clipped, Gumbel/SPARTA-gated targets and a frozen value. *Distinct:* The review's top untried fix for this mechanism; differs from the failed hard-target variants. *Cost:* medium
  - Probe whether the encoder represents KO-after-PlusPower (linear probe). *Distinct:* 'Learning, not inputs' is inferred from an input audit, never tested. *Cost:* low
- **New hypotheses (section 6):** H79, H80

### H07 · N2 · partly-supported (weak) · Draw-Trainer restraint is a pilot artifact

- **Mechanism:** Energy-heavy decks come from a pilot that leaves draw Trainers unplayed, so drafting learns that Trainers are worth less than Energy.
- **Verdict:** Weakly refuted as the cause of the Energy count, and only in meta-99's stall field: adding about 4 draw Trainers in place of Energy (0.501->0.427) and forcing draw cards first (0.418, deck-outs 469 vs 153) both lost there, and #127 traces the 36.5 Energy to the drafting ratchet. Not refuted: pilots do end turns holding playable draw Trainers (20,389 of 29,723) and misplay search, disrupt and tempo Trainers in the human lists (#32-#33, #92, #96). No swap or forcing test has used a search-strength pilot.
- **Tests:**
  - #32, #33: 24 human lists under a4-tok, Trainer->basic Energy: originals score PlusPower 41.8, Bill 45.8, CS 46.6, Oak 68.2 (DCE 55.9 is special Energy) (supports pilot artifact)
  - #68: meta-99 best decks, ~4 Energy -> Bill/Oak/CS (mean 4.3): 0.501->0.427 pilot, 0.475->0.385 SimpleBot; opponents the other stall decks (refuted in stall meta (confounded))
  - #69: draw_first.py on 12 meta-99 decks: Bill-first 0.513 +/- 0.020, Bill+Oak+CS first 0.418 +/- 0.020; deck-outs 469 vs 153; 2,304 games each (refuted (crude forcing))
  - #79: Sampled timing value Bill -0.19..+0.32, Oak -0.27..-0.06, CS -0.70..-0.37; greedy follow-through Bill +1.16, Oak +0.52 (supports timing deficit)
  - #80: Greedy-lines probe, base it79: all Trainers +1.32, Oak +1.36, Bill +0.74, CS +0.60 (supports timing deficit)
  - #82: base-cont: timing gap +1.32->+0.39; Oak play 0.037->0.104, Bill 0.116->0.231 (supports learnable deficit)
  - #85: SimpleBot both sides: meta-99 Trainer-light decks 0.58-0.62 vs human lists (neutral)
  - #92: Human lists: draw group 0.64-0.76 above Energy for every pilot; search/disrupt/tempo 0.36-0.52 (against narrow draw framing)
  - #96: psearch: Trainer-first puzzles 60->85-88%, PlusPower 31->81% (supports broader pilot artifact)
  - #126, #127: At 440: 26.5 basic Energy while deck-outs fell 59%->13%; 87-97% of moves were null Energy-for-Energy swaps (alternative cause (drafting ratchet))
  - #141: nodraw:15 on the human side vs walls: paired -0.002 [-0.009, +0.005], 571 of 576 games identical (draw management not what loses)
- **Do not repeat:**
  - ~4 Energy -> Bill/Oak/CS swaps on meta-99's best decks under the population pilot or SimpleBot (#68)
  - draw_first.py forcing (Bill-first, Bill+Oak+CS first) on meta-99 decks in self-play (#69)
  - card_ablation.py (each Trainer -> main basic Energy) on the archived lists under a4-tok, deckout-w0/w1 or SimpleBot (#32, #33)
  - trainer_value.py group-to-Energy panel on the archived lists under greedy learned pilots or SimpleBot (#92)
  - credit_diag.py --focus Trainer probe on pilot-v2, base it79, base-cont, ent-cont, explore-cont (#79, #80, #82)
  - --explore 0.1 mostly-greedy collection for Trainer timing (#81, #82)
  - nodraw:15 on the human side vs the walls (#141)
  - SimpleBot as a judge of Trainer value (#68, #92)
- **Untested variants:**
  - trainer_value.py / card_ablation.py among the human lists under psearch, for search/disrupt/tempo groups. *Distinct:* Only greedy/sampled pilots and SimpleBot were used; search is what fixes those groups (#96); adds little for draw cards. *Cost:* low
  - Energy->Trainer swap on the walls judged vs the human lists under psearch on both seats, with/without a 50-60-turn draw limit or the STS clock. *Distinct:* Tests whether a Trainer-heavier wall wins once both sides play at search strength. *Cost:* low-medium
  - Draft-time search judging (--judge-search, #148, uncommitted) while tracking whether accepted moves still cut Trainers. *Distinct:* Tests the mechanism at the drafting step rather than in evaluation. *Cost:* medium (1 screen, 20-40 iterations)
- **New hypotheses (section 6):** H80, H88, H89

### H09 · N2, N10 · refuted (moderate) · Less sampling teaches Trainer timing

**Evan:** his idea (rule 4: tried first and fully).

- **Mechanism:** Sampled follow-through erases a Trainer's payoff, so greedier collection would make it learnable.
- **Verdict:** The premise is refuted: 40 more ordinary sampled iterations (base-cont) cut the timing gain from +1.32 to +0.39 and added 54.9 Elo, while --explore 0.1 lost 116 Elo to base-cont and --ent 0.001 timed Trainers worse with neutral strength. This covers only rl/train.py runs from base it79 (1 seed per continuation, 2 from scratch), outside the metagame loop and with no decklist measure; explore-cont's loss is confounded with thin policy data, since the --policy-share control was never run.
- **Tests:**
  - #79: pilot-v2 Trainer probe: +0.97 greedy vs +0.52 sampled follow-through (motivating)
  - #80: base it79: timing gain +1.32 [0.99, 1.66] greedy vs +0.35 sampled (superseded by #82)
  - #82: explore-cont: Elo 19.4 vs it79 80.5 (-61), vs base-cont 135.4 (-116); KL 0.035-0.07 vs 0.017-0.026; grad clipped all 40 iterations (refuted (confounded by thin data))
  - #82: ent-cont: Elo 139.7 vs 135.4 (+/- 4.8); play 0.212 vs 0.326; timing +1.10 vs +0.39; SimpleBot 0.475 vs 0.514 (timing worse, strength neutral)
  - #82: explore10 x2 from scratch: 28.4/18.1 vs base 85.1/106.2; early lead vs pilot-v2 at it19 0.463/0.403 vs 0.372/0.376, lost after ~40 (refuted)
  - #82: base-cont (40 ordinary iterations): timing +1.32 -> +0.39 [0.12, 0.64], +54.9 Elo, play 0.225->0.326 (premise refuted)
  - #107-#108: 010-pilot-ent02-b (--ent 0.02, opposite direction): competence 0.491 vs 0.496; Elo +0.7 [-11.0, 12.4] (flat)
  - #128-#129: --judge-explore 0 from 460 (scr-judge, scr-judge-select): greedy 0.496 vs sampled 0.492; distance 37.2->36.5, 37.3->37.3; stopped after 461 (refuted (meta level))
- **Do not repeat:**
  - --explore 0.1 continuation, 40 iterations from base it79 (explore-cont, #82)
  - --explore 0.1 from scratch at base settings, 80 iterations (explore10, explore10-s2, #82)
  - --ent 0.001 continuation from base it79 (ent-cont, #82)
  - --ent 0.02 lab card 010-pilot-ent02-b, 290-310 (#107-#108)
  - --judge-explore 0 as the sole change from 460 (scr-judge, scr-judge-select, #128-#129)
  - Treating the it79 greedy-lines probe gap (+1.32 vs +0.35) as evidence that sampling blocks timing learning
- **Untested variants:**
  - --policy-share 0.1 (built in #82, never run). *Distinct:* Control only: separates thin policy data from greedy follow-through in explore-cont's loss; cannot itself improve timing. *Cost:* low; diagnostic
  - Collection at softmax temperature below 1 with behaviour log-probs recorded (off-policy corrected, e.g. importance-weighted / V-trace) (#80 Next). *Distinct:* Sharpens every decision instead of mixing argmax with full sampling, so does not thin the policy data. *Cost:* low-medium
  - Entropy weight annealed to 0 (#80). *Distinct:* Schedule only; weakly distinct since fixed 0.001 and 0.02 were both flat. *Cost:* low
  - Greedy follow-through only after decisions of a chosen option type, sampling elsewhere. *Distinct:* Closest to the probe's design; must be stated without 'Trainer' to satisfy Rule 2. *Cost:* medium

### H10 · N2 · refuted (moderate) · More pilot exploration (entropy 0.02)

- **Mechanism:** A larger PPO entropy bonus makes the pilot try, and so learn, Trainer lines it otherwise rarely samples.
- **Verdict:** The predicted +0.06 competence gain is refuted for --ent 0.02 over 20 iterations (010-pilot-ent02-b, 290-310, lr 1e-4, one decided fork): 0.491 vs 0.496, Elo +0.7 [-11.0, 12.4]. A small or slower gain, or a gain under the current recipe or a varied field, is not excluded: the realised policy entropy was never logged, and the components split (Trainer-value groups +0.02 to +0.05, Trainer-first puzzles 0.629 vs 0.680).
- **Tests:**
  - #103, #105: 010-pilot-ent02 (fork at 280, pre-deck-free line, one segment): +8.7 Elo [-11.1, 28.5] after 800 games; restarted as ent02-b (inconclusive (superseded))
  - #106: ent02-b at 300: -14.1 Elo [-26.7, -1.5] after 2,000 games; no sequential verdict (negative reading)
  - #107: ent02-b at 310: -6.9 [-26.4, 12.5] after 800 games under wrong (superiority) rule; requeue dropped 'decide: s1' (superseded rung; lab fault)
  - #108: Decided at 310: competence 0.491 vs 0.496 (bar 0.06); Elo +0.7 [-11.0, 12.4]; tempo .381/.335; Trainer-first .629/.680; PlusPower .500/.563 (refuted (predicted size))
  - #81-#82: ent-cont (--ent 0.001): Trainer play 0.212 vs 0.326; timing +1.10 vs +0.39; Elo 139.7 vs 135.4 (less exploration hurts Trainer play)
  - #81-#82: explore-cont: -116 Elo vs base-cont, play 0.181, timing +1.87; explore10/-s2 28.4/18.1 vs base 85.1 (less exploration hurts)
  - #103, #105, #106: Distilling hard search targets raised entropy +0.27/+0.29 with -56/-37 Elo (confounded by noisy targets)
  - #109: Main population went 10/29/20 -> 33/8/20 Pokémon/Trainers/Energy between 300 and 313, inside ent02-b's window (confound)
- **Do not repeat:**
  - --ent 0.02 fork 010-pilot-ent02-b from 290 to 310 at lr 1e-4 (#106-#108)
  - --ent 0.02 one-segment fork from 280 on the pre-deck-free line (010-pilot-ent02, #103/#105)
  - --ent 0.001 continuation from base it79, 40 iterations (ent-cont, #81-#82)
  - --explore 0.1 as continuation and from scratch (explore-cont, explore10, explore10-s2, #81-#82)
  - Raising pilot entropy through distilling hard one-turn search targets (exit, exit-h2, #105-#106)
- **Untested variants:**
  - Longer dose of --ent 0.02 (or 0.03-0.05) over 60-80+ iterations under the current recipe (lr 2e-4, type-capped varied field), logging policy entropy. *Distinct:* #82 showed Trainer timing takes ~40 iterations to emerge; the decided fork ran 20 and its dose was unverified. *Cost:* medium (1 lab card)
  - Sampling temperature above 1, an entropy target, or an annealing schedule, with behaviour log-probs recorded. *Distinct:* Controls realised entropy directly rather than through a coefficient (#109: a bonus cannot reopen a collapsed policy). *Cost:* low-medium
  - Exploration aimed at rarely chosen legal options (epsilon-uniform over options at a share of decisions, or a count bonus per option kind). *Distinct:* Targets rarely tried low-rated options rather than spreading mass globally; game-agnostic under Rule 2. *Cost:* medium
  - --policy-share 0.1 control (built in #82, never run). *Distinct:* Separates thin policy data from greedy follow-through; diagnostic only. *Cost:* low
  - --ent 0.02 with the pilot trained on a varied or wide-deck practice field. *Distinct:* Removes the #109 population confound so extra exploration meets Trainer-rich decks. *Cost:* 1 screen
  - [outside research] Exploration methods: adaptive entropy targets, count/RND bonuses over combinatorial legal options, Go-Explore restarts from saved states, delayed-payoff exploration. *Distinct:* None covered by the first review; the remaining in-system variants are blunt. *Cost:* deep research

### H11 · N2, N10 · refuted (moderate) · Expert iteration with hard search targets

- **Mechanism:** Distilling the best option found by one-turn search into the policy should move search's play-time gains (Trainer-first 60% -> 85-88%, PlusPower 31% -> 81%) into the trained pilot.
- **Verdict:** Refuted only for hard one-hot argmax targets from 2-4 re-dealt lines scored by the live pilot's own value, gated on best-minus-worst (margin 0.02 or 0.15), at distill weight 0.3-1.0. Each arm ran one seed and one segment and lost 37-79 Elo (exit-strong, exit, exit-h2). Distilling search in general is not refuted: soft, gated, frozen-value targets (EI v4), weights below 0.3 and runs long enough to reach a competence decision are untested, and exit-strong did raise Trainer-first puzzles from 0.577 to 0.680.
- **Tests:**
  - #50: psearch beats its own greedy pilot 65.4% ± 6.0 but not SimpleBot (82.5% vs 81.7%), so search scored by the pilot's own value may not transfer. (prior warning (predicted failure))
  - #96: Play-time search on puzzles: Trainer-first 60% -> 85-88%, PlusPower 31% -> 81%. Smoke distill fork: 31 targets, CE 2.68, 35% agreement, grad norm 27 at weight 1. (motivation; smoke only)
  - #103 exit-strong: -78.6 Elo [-114.3, -44.5] after 400 games. Competence 0.442 vs 0.480 (inside the 0.06 A/A bar); Trainer-first 0.577 -> 0.680, PlusPower 0.563 -> 0.313. (refuted on Elo; competence mixed)
  - #103 target probe h2: Counting fork of seg_0280 (200 games, not training): 411 targets vs 688, 250 differ from played move; benching 21 vs 55, pass 30 vs 10. (mixed (target composition only))
  - #105 exit: Weight 0.3, 2 lines: -56.1 Elo [-89.4, -23.8]; 935-997 of ~1,000 probes became targets; 45% agreement; entropy 0.72 -> 0.99. (refuted for this configuration)
  - #106 exit-h2: Horizon 2, margin 0.15, on deck-free line 290-300: -36.6 Elo [-62.8, -10.9]; entropy 0.61 -> 0.90; 37% agreement, CE 1.51. (refuted for this configuration)
  - #106 lethal-only: One-iteration smoke: 1 target in 1,194 probes, and it equalled the played move, so zero informative targets. (no information)
  - #146, #147: One-turn search on both seats still ranks walls first (0.57-0.59); two-turn 0.571 vs one-turn 0.531 on 49 deals. (bounds the drafting payoff of perfect distillation)
- **Do not repeat:**
  - exit-strong exactly: --distill 1.0 --search-p 0.25 --search-max 4 --search-options 8 --search-lines 4 --search-prize 0.1, default margin 0.02, horizon 1 (#103)
  - exit exactly: --distill 0.3 --search-p 0.1 --search-max 2 --search-options 6 --search-lines 2, default margin 0.02 (#105)
  - exit-h2 exactly: --distill 0.3 --search-horizon 2 --search-lines 4 --search-options 6 --search-margin 0.15 (#106)
  - --search-lethal --distill 1.0 --search-p 0.3 --search-max 6 --search-options 8 --search-lines 4 on uniformly sampled main-phase probes, while lethal mode defaults to the played option (#106)
  - Hard argmax targets gated on the best-minus-worst range and scored by the live, being-trained pilot's value (#103, #105, #106; #50 self-reference)
- **Untested variants:**
  - EI v4: Gumbel top-k, soft clipped targets gated at 2 SE, frozen leaf value. *Distinct:* Addresses all three diagnosed causes (hard argmax, near-zero margin, self-referential value). The frozen value must be named: a population pilot carries the walls bias and pilot-v2 judges very differently (0.26 vs 0.72). Even perfect one-turn distillation still ranks walls first (#146). *Cost:* medium
  - Distill weight 0.03-0.1, or distill loss normalised over all rows rather than searched rows only. *Distinct:* Dose test: the current loss normalisation makes weight 0.3 a large share of the gradient (grad norm 27 at weight 1), and no lower weight was run. *Cost:* low
  - Targets scored by the game's own prize result within the turn, with no value (the #95 plan). *Distinct:* Removes the self-referential value; the build added --search-prize on top of the value, so this was never run. *Cost:* low
  - 8-16 lines per option with a best-vs-chosen (or best-vs-runner-up) SE gate. *Distinct:* Reduces target noise and stops near-ties producing hard targets; the coded gate compares best with worst. *Cost:* medium
  - Run past the first-segment Elo gate for 2-3 segments to a competence decision. *Distinct:* Separates a transient first-segment cost from a lasting one; competence was measured only for exit-strong. *Cost:* medium
  - Lethal targets on late-game probes, only where the played option did not win. *Distinct:* Only changes where probes are sampled; informative only for Trainer-first or PlusPower lethals (113 of 408 puzzles), since attack lethals are already solved 86-94%. Expect low yield. *Cost:* low
- **New hypotheses (section 6):** H72, H105, H106

### H12 · N2 · untested (weak) · Model-based search in learned action-sequence space

- **Mechanism:** A learned prefix-LM over action sequences searched with Gumbel MCTS would search without Game.clone re-dealing of hidden cards, removing the engine-cloning dependence for MTG; the state representation would still be Pokémon-specific.
- **Verdict:** Design only (#51, notes/design-action-sequence-search.md): no sequence logger, prefix-LM or Gumbel code exists. Its step-3 expert iteration shares the mechanism of the failed hard-target runs (#103-#106), and engine search on both seats only narrows the walls' margin (#146-#147), so even success would not by itself flip the verdict.
- **Tests:**
  - #13: Flat Monte Carlo with determinization via Game.clone: noise around the heuristic (25.0% and 37.5% with 4 rollouts). (related; origin of engine-cloning dependence)
  - #50: psearch (k 4, dets 4) beats its own greedy pilot 65.4% but not SimpleBot (82.5% vs 81.7%). (related; 'match psearch' is not a useful gate)
  - #51: Design written; 'Design only; nothing built or measured'. (untested)
  - #103, #105, #106: Engine expert iteration with hard targets: -79, -56, -37 Elo; targets differ from pilot on 60-70% of probes; entropy +0.27 to +0.29. (related; step 3 risk with hard targets)
  - #146, #147: One-turn engine search on both seats 0.573-0.592 vs greedy 0.706-0.734; two-turn not better; only with 50-60 turn draws 0.44-0.46. (related; ceiling on search strength for the verdict)
- **Do not repeat:**
  - Hard one-hot argmax expert-iteration targets from 2-4 re-dealt lines scored by the pilot's value (#103 weight 1.0, #105 weight 0.3, #106 horizon 2 margin 0.15); H12's visit-count targets must be soft and gated
  - Lethal-only exact targets at uniform random probes (#106: 1 in 1,194)
  - A step-2 gate of 'match psearch against SimpleBot' (#50: psearch does not beat SimpleBot); use past snapshots, other runs or the walls-vs-human-lists panel
  - Starting from arch-A..D fine-tunes (#49), or training against SimpleBot or archived lists (excluded by rule 1, #51)
- **Untested variants:**
  - Step 1 only: sequence logger plus offline prefix-LM, checked for k-step policy/value agreement, legality accuracy and chance log-loss. *Distinct:* Cheap gate on whether a learned model is accurate enough before any search is built. *Cost:* low-medium
  - Step 2: hybrid search with the learned model but engine-provided legal sets. *Distinct:* Tests the model's planning value separately from legality modelling. *Cost:* medium
  - Step 3 via EI v4 on the existing engine psearch first. *Distinct:* Same soft-target mechanism as H12's step 3 at far lower cost; if it fails there, H12's step 3 is unlikely to work. *Cost:* medium
  - Full engine-free 16-32-simulation Gumbel MCTS on the prefix-LM. *Distinct:* Needs neither a cloneable engine nor game-specific re-dealing of hidden cards. *Cost:* high
  - Design alternatives: Stochastic MuZero abstract chance codes vs card-shaped chance tokens; EfficientZero-style consistency head; determinized vs implicit opponent hidden hand. *Distinct:* Each design choice is untested and changes how chance and hidden information are modelled. *Cost:* medium each
  - [outside research] Stochastic MuZero (Antonoglou 2022), Sampled MuZero (Hubert 2021), Player of Games (Schmid 2021), belief-state planners. *Distinct:* Learned-model search under hidden information and chance was not covered by the first review; needed before the high-cost build. *Cost:* deep research

### H13 · N2 · adopted (weak) · PPO update settings

- **Mechanism:** Fewer PPO epochs cut compute without losing strength; a larger learning rate was meant to speed pilot learning, but faster learning has not been shown.
- **Verdict:** 2 PPO epochs was adopted on a noninferiority test (+8.7 Elo [-9.7, 27.1]) plus a measured speed-up (14.7 vs 18.1 min a segment), and lr 2e-4 on one fork's +13.8 Elo, about 1.5 sigma of A/A fork noise and confounded by the lr fork importing a non-collapsed population. Neither was replicated, neither raised pilot competence, and neither bears on the Energy-heavy minimum.
- **Tests:**
  - #86: A/A noise: sigma 8.8 Elo a segment; reseeded A/A fork -13.3. (noise bar)
  - #87: 2 epochs noninferiority: +8.7 [-9.7, 27.1]; archived +40.5 [22.4, 58.8] one fork; segment 14.7 vs 18.1 min, iteration 92.1 vs 108.3 s. (adopted (cheaper, not worse))
  - #90, #97: Fork with no pilot change read +29.6 [18.6, 40.7], replicated at +0.0. (fork-luck precedent)
  - #107: lr 2e-4 at 310: +8.7 [-7.8, 25.2] after 1,200 games. (not significant)
  - #111: lr 2e-4: +13.8 [4.3, 23.3] after 2,400 games; archived gate at 320 +5.0 [-13.0, 23.1]. (adopted on one fork)
  - #112: From 300, lr 1e-4 line collapsed to ~31/8/20; lr2 fork kept 13-17 Pokémon / 23-28 Trainers; adopt() imported lr2's population. (confound)
  - #113: lr 2e-4 doubled KL 0.0119 -> 0.0236, clip fraction 0.100 -> 0.160; deep6 +14 under 1e-4, -25 under 2e-4. (side effect; more fork noise)
  - #114, #116: Competence 0.496 (310), 0.472 (320), 0.447 (360); lr counted among cards that never moved competence. (no competence gain)
  - #117, #118: From-scratch run of the adopted recipe (lr 2e-4, 2 epochs) still collapsed toward Pokémon piles. (not an isolated test)
- **Do not repeat:**
  - One-fork lab card 2 vs 3 PPO epochs decided on the drafted-panel Elo gate (#87)
  - One-fork lab card lr 2e-4 vs 1e-4 where the arms' populations diverge (#107, #111)
  - Crediting a deck-shape outcome to lr 2e-4 from the 300-320 fork pair (#112)
- **Untested variants:**
  - Learning-rate decay schedule (expose --lr-final/--lr-decay-* from rl/train.py in rl/metagame.py). *Distinct:* Addresses late-training stability and drift, which could bear on relapse; no lr-decay run in the log. *Cost:* low
  - KL-target early stop of PPO epochs. *Distinct:* Adapts update size to KL, which doubled at lr 2e-4 (#113). *Cost:* low
  - Minibatch size other than the default 4096. *Distinct:* Never varied in the lab. *Cost:* low
  - Population-controlled lr comparison: both arms on a shared frozen deck set, or several replicate forks. *Distinct:* Test-design variant; the only way to tell whether lr 2e-4 itself helped. *Cost:* medium
  - lr above 2e-4, or 1 PPO epoch. *Distinct:* Same mechanism, different step; low value. *Cost:* low

### H14 · N2, N4 · weakened (moderate) · Pilot first: fix Trainer play and drafting follows

- **Mechanism:** The drafting judge misplays Trainers, so fixing the pilot's Trainer play first would remove the judge's bias and the decks would follow.
- **Verdict:** Training-based pilot fixes (the 16 cards of #116, three hard-target expert-iteration forms, human-list and wide practice, varied field, KL anchor, lam-value 1) never raised Trainer competence (0.43-0.48 since 160), so 'raise competence and the decks move' is untested; pilots made more general on the human lists left the walls' verdict at 0.68-0.75, and #137 places the bias in the walls' pilot's deck-out plan rather than in human-side Trainer misplay. Only play-time search raised competence, and as a judge it moved the walls part of the way (0.71 -> 0.57), not below 0.5 without a 50-60 turn draw limit.
- **Tests:**
  - #96: Play-time search: Trainer-first 59.8% -> 84.5-87.6%, PlusPower 31% -> 81%. (only lever that raised competence)
  - #103, #105, #106: Expert iteration on that search, hard targets: -79/-56/-37 Elo; lethal-only targets too rare. (failed to bake search into the pilot)
  - #114: At 360 decks reached 29 Trainers (distance 11.5) while competence fell to 0.447. (counter-evidence to the causal order)
  - #116: 16 pilot cards; none moved competence by 0.06 (slotbind-w +0.013; main 0.480/0.472/0.447 at 280/320/360). (inconclusive (premise unmet))
  - #127, #131, #133: Human-list practice 0.25 -> 0.31 in 20 iterations; population pilots still rate main decks 0.75-0.83. (no move)
  - #132, #134: pilot-v2 as second judge (share 0.5) pulled decks toward Pokémon piles, not human types. (refuted for that configuration)
  - #134, #137: Varied type-capped field pilots general (resetcap -22.7, resetent +2.8 Elo for pilot-v2); decks stayed walls. (generality did not move decks)
  - #137: Walls' pilot / human pilot: own/own 0.720, own/v2 0.761, v2/v2 0.237, v2/own 0.233. (verdict follows walls' pilot)
  - #138: scr-anchor 460-472: pilot-v2 -41.7 vs control +30.0/+25.2 (~65-70 Elo); shape 28.7/24.8/25.3 like control; both arms --draft-ent 0.05. (underpowered (12 iterations))
  - #139, #146, #147: Search judges: human side 0.578; both sides 0.573-0.592; two-turn 0.571 vs 0.531 (49 games); with 50-60 turn draws 0.44-0.46. (partial support for a stronger judge)
  - #145, #147: --lam-value 1 (scr-lamv479) relapsed; judge 0.712. (no move)
  - #147: Ten population pilots rate walls 0.676-0.746 (SE ~0.013, 1,152 games each); pilot-v2 0.264, attributed to deck-out-0 training. (static judge; training changes did not move it)
- **Do not repeat:**
  - The 16 pilot cards of #116: history-token memory, attention memory, GRU; deck-free encoder cold and warm; expert iteration at weights 0.3 and 1.0 and less-myopic targets; --lam-turn 1; lasting shaping; entropy 0.02; lr 2e-4; 6- and 8-layer pilots; slot binding cold and warm
  - Expert iteration with hard one-hot targets from one-turn search (#103, #105, #106); lethal-only targets at random probes (#106)
  - KL anchor to pilot-v2 at --anchor-w 0.1 on practice games only, from 460 (#135, #138)
  - Human lists on one side of 30% of games as a diagnostic (#127, #131)
  - 250 wide-random practice games an iteration as a generality fix (#133)
  - Type-capped varied field (turnover every 5) as a generality fix (#137)
  - Static greedy judge comparison of further population pilots (#147)
  - --lam-value 1 Monte Carlo value targets in the loop (#145, #147)
  - pilot-v2 as second judge at --judge-share 0.5 from 460 (#132, #134)
- **Untested variants:**
  - Judge with play-time search in the drafting loop (--judge-search, #148; family H23). *Distinct:* Strength at judging time without weight change. Running, no results logged; static tests predict walls stay on top without --max-turns, so read with a draw limit. Double-counts H23. *Cost:* running
  - Expert iteration v4 with soft, clipped, gated (Gumbel/SPARTA-style) targets. *Distinct:* Only remaining route to a pilot stronger after training rather than at play time; differs from #103-#106's hard argmax. *Cost:* medium
  - Judge pilot trained with deck-out wins paid 1 vs 0, or under a 60-turn draw rule. *Distinct:* Reward shapes the judge, not its competence; #147 traces pilot-v2's 0.26 to this choice. Check with Evan against rule 2 first. *Cost:* medium
  - Training-only critic that sees hidden zones; auxiliary outcome heads. *Distinct:* Targets competence through value quality; distinct from all #116 cards. *Cost:* medium
  - [outside research] Distilling search in imperfect-information games (ReBeL/Student of Games-style). *Distinct:* Warranted only if search judging (H23) also fails to flip the verdict without a draw limit. *Cost:* deep research
- **New hypotheses (section 6):** H106

## N3 · Pilot generality across deck types

### H15 · N3 · supported (moderate) · The shared pilot specialises to its field and forgets other decks

- **Mechanism:** One pilot trained on the population's one-type decks gets better at that type and worse at other decks.
- **Verdict:** Population pilots play the human lists 27-45 Elo worse than pilot-v2 (#134, four sibling forks of one lineage), and the independent meta-99 lineage agrees (0.724 vs 0.817 vs SimpleBot, #74). That the cause is specialisation to the field is not separated from pilot-v2's deck-out-0 reward, architecture and league. The varied-field remedy rests on one training seed (resetcap -22.7 vs scr-reset +44.6), is contradicted by human-list practice (+44.3) and wide practice (+27.1), and leaves the walls at 0.68-0.75, so forgetting is not the lever that moves decks.
- **Tests:**
  - #18, #20: One MLP for 24 human decks ~9 points below a specialist; Rain Dance low figure partly an environment fault. (unrelated (multi-deck capacity))
  - #74: 40-it pilots: human 0.27-0.38 vs held-out population 0.51-0.61 (learning order). meta-99 final pilot 0.724/0.777 vs pilot-v2 0.817/0.565. (supported (meta-99 lineage only))
  - #86: Answer key 0.72 under main pilot vs 0.48 under pilot-v2 at 160; reseeded A/A -17.0 [-35.0, 0.8]. (supported; sets noise floor)
  - #87: 2-epoch branch +40.5 [22.4, 58.8] on archived lists after one segment. (weak support (one fork))
  - #98, #114: Main line 82.1% ± 3.4 vs SimpleBot on human lists at 240 (= pilot-v2 82%); own decks 0.926 -> 0.971 (280-360). (neutral (no decline by 240))
  - #127: Hitmonchan variants lose under main pilot but beat main decks 0.72-0.97 under pilot-v2. (supported)
  - #131, #134: diag-human-practice (human lists 30% of games, 20 it): pilot-v2 still +44.3 [24.5, 64.4]; human lists 0.25 -> 0.31. (contradicts remedy at this dose)
  - #133, #134: scr-practice (250 wide games/it, 30 it) +27.1 [8.1, 46.3] vs unpractised +39.8; intervals overlap. (null remedy)
  - #134: Four sibling-fork population pilots trail pilot-v2 by +27 to +45 Elo on human lists. (supported (one lineage))
  - #135: anchor_kl 0.823 nats a decision between main 460 pilot and pilot-v2 on wide decks. (supported)
  - #137, #138: resetcap -22.7 (seed-0 eval -18.9) vs scr-reset +44.6; resetent +30.0/+25.2/+2.8 at 469/479/496; one training seed. (mixed)
  - #138: KL anchor w 0.1: pilot-v2 -41.7 [-60.8, -22.9] at 472 vs control +30.0. (anti-forgetting works; decks unmoved)
  - #147: All population pilots, including the most general (resetcap 0.722, resetent 0.734, anchor 0.694), rate walls 0.68-0.75. (forgetting is not the lever)
  - #54-#57: League with per-agent pilots; generalist 76.0% ± 4.2 vs SimpleBot on archived decks; lineages drifted to Pokémon/Energy piles. (per-niche pilots already tried)
  - #115: Incoming-entropy floor cards cost the pilot 27-33 Elo on the drafted panel. (supported (skill tied to field))
- **Do not repeat:**
  - h2h pilot-v2 vs population pilots at 460-499 with extra eval seeds only (#134, #137, #138); replicate with new training seeds instead
  - Human lists as fixed decks on one side of 30% of games, 20 iterations from 450, as a forgetting cure (#127, #131, #134)
  - 250 wide-random practice games an iteration as a forgetting cure (#129, #133, #134)
  - KL anchor to pilot-v2 at w 0.1 on practice games from 460 (#135, #138)
  - Separate per-agent pilot networks in a league from pilot-v2 without distillation (#55-#57)
- **Untested variants:**
  - Cluster-balanced or regret-curated PPO data plus a 20% past-population archive. *Distinct:* Decouples the PPO data balance from the judging population and replays past decks; type-cap already balances by type on one seed, so only the decoupling and archive are new. *Cost:* medium
  - Per-niche pilot heads with distillation into one generalist. *Distinct:* Only the distillation is new (#54-#57 tried per-niche pilots); risks strengthening F2 since each niche's judge favours its own type. *Cost:* high
  - Deckout0 ablation arm planned in #73. *Distinct:* Separates field specialisation from pilot-v2's deck-out-0 objective; never reported. *Cost:* medium
  - Decklist dropout / decklist-overfitting check (#74). *Distinct:* Directly tests overfitting to specific lists; proposed, never run. *Cost:* low
  - Training replicates (new --reseed) of scr-resetcap vs scr-reset. *Distinct:* Establishes the varied-field effect beyond ~17 Elo fork noise. *Cost:* medium
  - Anchor stacked with the gate and varied field from 460 (#138 Next). *Distinct:* Combination never run. *Cost:* medium
- **New hypotheses (section 6):** H91

### H16 · N3, N4 · refuted (moderate) · A more general pilot (wide practice, KL anchor) frees the decks

- **Mechanism:** If the walls win through a specialised pilot, a more general pilot would let other deck types win places.
- **Verdict:** Pilots as general as or more general than pilot-v2 on the human lists (scr-resetcap -22.7, scr-resetent +2.8, scr-anchor -41.7 Elo for pilot-v2) still rate the walls 0.69-0.73 against pilot-v2's 0.264 (#137, #147). The configurations covered are 250 wide practice games an iteration, a type-capped varied field, a KL anchor of 0.1 on practice games, pilot-v2 as co-judge, and frozen pilot-v2 drafting. Practice above 250 games, an anchor on population games, and a moving-reference anchor are untested, and the verdict follows the walls' pilot's stall-to-deck-out skill rather than generality.
- **Tests:**
  - #127: Main pilot 450 rates main decks 0.784-0.826 vs human lists; pilot-v2 0.253-0.263; Hitmonchan variants flip. (origin of hypothesis)
  - #130: scr-draft (removed practice, --turnover-wide, --protect 20) vs scr-practice, 460-465: shape moved with drafting changes, not practice. (inconclusive (5 it, 3 factors))
  - #131: scr-v2 frozen pilot-v2 drafting wide decks: median Pokémon 15 -> 23 in 4 iterations. (refuted for this configuration)
  - #131, #133, #134: diag-human-practice: human lists 0.25 -> 0.31; main decks 0.749-0.761 vs them; pilot-v2 still +44.3. (no move)
  - #132, #134: scr-judge2 (pilot-v2 judge share 0.5 from 460): more Pokémon, deck-outs to 48%, stopped as stalled. (refuted for this configuration)
  - #133: Walls judged: scr-practice 0.789-0.820, scr-reset (also practised) 0.749-0.775, main 0.784-0.826. (no move)
  - #134: scr-practice +27.1 [8.1, 46.3] vs scr-reset +44.6 [25.9, 63.6]; both had 250 practice games. (null on generality)
  - #135, #138: scr-anchor 460-472: pilot-v2 -41.7 [-60.8, -22.9] vs control +30.0/+25.2; shape as control; --draft-ent 0.05; one seed. (pilot generalised; decks underpowered)
  - #137: Varied-field pilots general (-22.7, +2.8); walls own/own 0.720, own/v2 0.761, v2/v2 0.237, v2/own 0.233. (refuted)
  - #141: Walls' edge holds with human side barred from draw cards (0.702 vs 0.701). (deficit is prize-race tactics)
  - #145: Challenger practice: largest type 60 vs 48 at 489, equal at 494 (72 vs 74). (no gain)
  - #147: As judges: scr-anchor 0.694, resetent 0.734, resetcap 0.722; all population pilots 0.68-0.75 vs pilot-v2 0.264. (refuted)
- **Do not repeat:**
  - --practice-games 250 wide random decks (scr-practice, #129, #133)
  - --draft-reset with --practice-games 250 (scr-reset, #130-#134)
  - --anchor pilot-v2 --anchor-w 0.1 on practice games only, with --draft-reset --draft-ent 0.05 --type-cap 0.5 --turnover-every 5 from 460 (scr-anchor, #135, #138)
  - --type-cap 0.5 --turnover-every 5 as a pilot-generality lever (scr-resetcap, scr-resetent, #137)
  - --judge-pilot pilot-v2 --judge-share 0.5 from 460 with scr-reset's flags (scr-judge2, #132, #134)
  - --init-from pilot-v2 --freeze-pilot --init-wide (scr-v2, #131)
  - --practice-games 250 --practice-vs 0.5 --practice-vs-from pop from 479 (scr-vs479, #142, #145)
- **Untested variants:**
  - Anchor to a moving reference (R-NaD/NeuRD-style lagged snapshot). *Distinct:* Regularises toward the policy's own lagged snapshot to damp cycling, not toward deck-out-0 pilot-v2; but the reference is the population's own biased pilot. Needs outside reading (DeepNash) first. *Cost:* medium
  - Random-card replacement in recorded population games. *Distinct:* Perturbs decks near the population rather than wide random decks; its aim (deck-robust pilot) was already reached without moving the verdict. *Cost:* low
  - Practice dose above 250 games (scr-practice1k) and --draft-ent 0.1 (scr-resetent10). *Distinct:* Both killed within ~6 iterations for memory (#136) and never read. *Cost:* medium (memory)
  - Anchor stacked with gate and varied field without entropy bonus (#138 Next), or anchor applied to population/judging games. *Distinct:* The tested anchor constrained only practice-game decisions and the head was pinned by --draft-ent 0.05; low expected gain since pilot-v2 is not an unbiased judge. *Cost:* medium
- **New hypotheses (section 6):** H73, H86, H91, H105, H108

### H17 · N3, N8 · refuted (moderate) · Challenger practice breaks the incumbents

- **Mechanism:** Training from the challengers' side against the best decks teaches the play that beats them, so challengers score more and relapse slows.
- **Verdict:** Population challengers in practice games under the shared pilot (--practice-vs 0.5 from pop, forked at 479, one seed, 16-20 iterations, with and without the gate) had a null effect: shape, type size and the judge's walls score (0.746 vs 0.714; 0.676 vs 0.680) match controls, and even the human lists as ideal challengers moved only 0.25 -> 0.31. A separate best-response pilot, non-wall-only challengers, and challengers with search are untested, and faster relapse was not shown.
- **Tests:**
  - #141: Wide random challengers, one iteration: 0.0 over 20 games; CUDA OOM at 481. (design check: no PPO signal)
  - #142, #145: scr-vs479: challengers 0.24-0.36; largest type 11/60/72 vs control 33/48/74 at 484/489/494; distance 17.8 vs 17.0 at 494; stopped 495. (null (not faster relapse))
  - #143, #146: scr-gatevs479: top-12 distance 9.7 vs 9.5 (490-499); Chansey+Snorlax 70 vs 73 at 499. (null)
  - #147: Judge of walls vs human lists: scr-vs479 0.746 vs scr-ctl479 0.714; scr-gatevs479 0.676 vs scr-gate479 0.680. (refuted (null))
  - #131, #134: Human lists as challengers 30% of games, 20 it: 0.25 -> 0.31; main decks 0.749-0.761; pilot-v2 +44.3 [24.5, 64.4]. (upper bound: ideal challengers barely move it)
  - #129, #130, #133: scr-practice: shape moved via drafting, not practice; practised pilot rates walls 0.789-0.820. (related null)
  - #140: Replicate gap: scr-ctl479 15.7 vs scr-resetcap 17.2 mean distance over 490-499. (noise reference)
  - #55-#57: Separate-network exploiters went 0.00/0.06 -> 0.94/0.81 vs leading deck in one round (pre-walls). (related; separate pilot works)
  - #123-#125, #143, #146: Exploiter draft heads scored 0.508/0.452/0.541 vs head 0 and drafted the same walls. (related null)
- **Do not repeat:**
  - --practice-vs with wide random challengers (default --practice-vs-from) (#141)
  - scr-vs479: --practice-vs 0.5 --practice-vs-from pop --practice-games 250 from scr-resetcap/population_it0479.pt with scr-ctl479's recipe (--candidates 3)
  - scr-gatevs479: the same plus --candidates 1 --select-z 1.0
  - --fixed-decks the 24 human lists as practice opponents (diag-human-practice; diagnostic only, rule 1)
  - More wide-vs-wide practice games under the shared pilot as a lever on the judge (scr-practice, #133)
- **Untested variants:**
  - Separate best-response pilot trained against the walls, playing drafted non-wall decks. *Distinct:* Removes the shared judge (F2); #55-#57 exploiters were pre-walls. Starting from pilot-v2 carries its deck-out-0 bias. *Cost:* low-moderate (~3.5 GB GPU)
  - Challengers drawn from non-wall types only (type-filtered pool, #138 'challenger niche'). *Distinct:* Removes the walls-lite confound: 73-79 of 99 population decks held Chansey and Snorlax. *Cost:* medium
  - Challenger practice with search-strength play on the challenger side (#141 Next). *Distinct:* Search on both sides plus a 50-60 turn draw limit is the only setting ranking walls below the human lists (0.44-0.46). *Cost:* medium-high
- **New hypotheses (section 6):** H87, H100, H105

## N4 · The judge

### H18 · N4 · supported (moderate) · Deck verdicts depend on the judging pilot (F2)

- **Mechanism:** A pilot plays best the decks it trained on, so a shared judge inflates its own population's decks.
- **Verdict:** That the same decks get very different verdicts from different pilots is established (walls 0.68-0.75 under every population pilot, 0.264 under pilot-v2; 0.81/0.67/0.28 across three judges at 360). Own-pilot inflation is not established: the walls' own pilot is not the highest judge (0.722), the dissenting pilot-v2 has a deck-out-0 handicap, non-co-adapted SimpleBot also rates them 0.67, and one-turn search on both seats still gives 0.57-0.59 under clockless rules.
- **Tests:**
  - #17: SimpleBot Nash of the human lists leaves Haymaker (7 of 24 lists, best list -0.17) outside the support. (indirect (one judge))
  - #40: Same deck 60.7 -> 71.9 under the loop's own final pilot (+11). (partly supported (#41 shows a general lift too))
  - #41: Greedy mixture beats stochastic 75.8 under greedy loop's pilot vs 59.4 under stochastic loop's. (supported (clean own-pilot contrast))
  - #42, #43, #46: Scratch-pilot decks 55-72 under it, 32-46 under result #1's pilot; four variants spread 2 vs 18 points. (supported (judge dependence))
  - #85, #86, #89: Answer key 0.72 (main) vs 0.48 (pilot-v2) at 160; snapshots 99 vs 149 ordered differently; pilot-v2 rose 0.20 vs SimpleBot 0.06. (supported)
  - #90: Answer key under own pilot 0.719 -> 0.794 while staples and overlap fell. (supported (familiarity))
  - #115: 360 best decks: 0.81 own / 0.67 SimpleBot / 0.28 pilot-v2; own-pilot reading 'an inference, not tested'. (supported; pilot-v2 is the outlier)
  - #127, #132: Walls 0.784-0.826 and 0.713-0.803 under own pilot vs 0.253-0.263 and 0.204-0.316 under pilot-v2; variants beat walls 0.72-0.97 under pilot-v2. (supported)
  - #131, #132, #134: Non-co-adapted judges in training (scr-v2, scr-judge2) drift toward Pokémon piles, not human types. (independent judge alone insufficient)
  - #137: own/own 0.720, own/v2 0.761, v2/v2 0.237, v2/own 0.233; resetcap pilot ~20 Elo better than pilot-v2 on human lists. (dependence follows the walls' pilot)
  - #139, #146, #147: Search judges: human side 0.572-0.578, both sides 0.573-0.592; 50-60 turn draws 0.44-0.46; STS rule 0.40-0.49. (part of 0.72 is real under clockless rules)
  - #147: Population pilots 0.676-0.746 (walls' own pilot 0.722, not highest); pilot-v2 0.264 attributed to deck-out-0 training. (dependence yes; own-highest no)
- **Do not repeat:**
  - probe_matchups.py on scr-resetcap 499 walls under the #147 pilots
  - probe_matchups.py four pairings own/v2 x own/v2 of the scr-resetcap 499 walls vs the 24 human lists (#137)
  - probe_matchups.py on the main line's 450 best decks plus probe-hitmonchan / probe-chan-buzz under main 450, diag 470, scr-practice 490, scr-reset 491 and pilot-v2 (#127, #131, #133)
  - rl.lab h2h --panel archived --fixed, pilot-v2 vs main 460 / scr-practice 490 / scr-reset 491 / diag-human-practice 469 / scr-resetcap 499 / scr-resetent 496 / scr-anchor 472 (#134, #137, #138)
  - --judge-pilot runs/pilot-v2/model_it00349.pt --judge-share 0.5 from 460 (scr-judge2)
  - --init-from pilot-v2 --freeze-pilot --init-wide (scr-v2, #131)
  - sb_archived (SimpleBot both sides) on meta-99 snapshots 49/99/149 (#85)
  - walls_vs_humans.js with one-turn psearch (k4 dets4) on the human side and on both sides, on #139's 192 deals
  - Re-scoring the walls' games with draws at T = 40/50/60/70/100 (#147)
- **Untested variants:**
  - Judge pilot trained like pilot-v2 but with deck-out wins paid 1. *Distinct:* Clean separation of own-pilot inflation from pilot-v2's deck-out-0 handicap; cheap and in-system. *Cost:* low-medium
  - Min over distinct pilots as fitness. *Distinct:* Current --judge-search (#148) is a min over two strengths of one pilot; a min over distinct pilots is untested but low value unless the set includes an unbiased judge. *Cost:* medium
  - Implement robust evaluation (alpha-Rank, max-min/PFSP-hard, exploitability). *Distinct:* Literature already covered by the first review (deckbuilding_ccg.md, population_game_theory.md); only implementation remains. *Cost:* medium
  - [outside research] Building a judge without stall/deck-out bias without game-specific shaping. *Distinct:* The one question the first review did not cover. *Cost:* deep research
- **New hypotheses (section 6):** H76, H82, H85, H86, H88, H90

### H19 · N4, N2 · weakened (moderate) · Human-side misplay explains the walls' rating

- **Mechanism:** The walls look strong because the human lists are played badly.
- **Verdict:** At the pilot strengths available (Trainer competence 0.43-0.48), better human-side play narrows the walls without flipping them in the clockless game (one-turn search 0.706 -> 0.578 [0.484, 0.677]), and with a 40-60 turn draw limit or the STS clock it puts them at 0.40-0.49, so misplay is a clock-dependent contributor rather than the main driver. Human-level human-side play is untested, since the practice diagnostic (#131) and the pilot swap (#137, ~20 Elo) barely changed human-side strength.
- **Tests:**
  - #131, #133: diag-human-practice: human lists 0.253-0.260 -> 0.313 at 469; walls 0.749-0.761 vs 0.784-0.826; shared pilot on both seats. (inconclusive (manipulation failed))
  - #134: diag pilot still 44.3 Elo [24.5, 64.4] worse than pilot-v2 on human lists after practice. (manipulation check failed)
  - #137: .720/.761/.237/.233, 2,304 games per pairing; human-side pilots differ ~20 Elo. (refuted within available strengths)
  - #138, #147: KL-anchor pilot ~65-70 Elo better on human lists still judges walls 0.694 (plays both seats). (weakens)
  - #139: Human-side psearch: 0.706 -> 0.578 [0.484, 0.677], paired -0.128 [-0.214, -0.042]; non-deck-out games 0.277; STS rule 0.400/0.426/0.486 at 40/50/60. (partial support)
  - #141: nodraw:15 on human side: 0.702 vs 0.701, paired -0.002 [-0.009, +0.005]; 571 of 576 games identical. (refuted (draw-out sub-mechanism only))
  - #145-#147: One-turn search both sides 0.592 (152 games), 0.573 [0.469, 0.677] (192). (walls' search adds little)
  - #147: Two-turn search both sides 0.571 vs one-turn 0.531 on 49 games (partial). (no gain yet)
  - #147: Human-side search with draws at T 40/50/60/70/100: 0.401/0.417/0.464/0.510/0.578. (supported with a clock)
  - #114, #119, #126: SimpleBot both sides rates walls 0.668/0.704/0.685 vs human lists. (third judge also >0.5)
  - #147: Population pilots 0.68-0.75; pilot-v2 0.264 attributed to deck-out-0 training. (walls' pilot dominates)
- **Do not repeat:**
  - --fixed-decks human lists on one side of 30% of games (diag-human-practice, diagnostic, #127, #131)
  - nodraw:15 on the human side (#141)
  - walls_vs_humans.js on #139's deals with psearch k4 dets4 one-turn on the human side (192 games) and on both sides (#145-#147)
  - probe_matchups.py four-pilot pairing swap of scr-resetcap 499 walls, 32 a pair (#137)
  - rl.lab h2h --panel archived --fixed of existing population pilots vs pilot-v2 (#134, #137, #138)
  - Judge sweep of today's screen pilots on the 3 walls vs 24 lists, 16 a pair (#147)
  - Re-scoring existing games under the STS round rule or draws at T turns (#139, #147); re-run only with pilots trained under that rule
  - SimpleBot both-sides answer key on wall populations (#114, #119, #126)
  - Restarting two-turn psearch both sides k4 dets4 (#147, partial at 49 games): finish it instead
- **Untested variants:**
  - Asymmetric best-response: separate human-side network fine-tuned by PPO on the human lists vs a frozen walls' pilot, with equal budget given to the walls' pilot. *Distinct:* #131's practice was two-sided through one shared pilot; a separate network isolates human-side strength. *Cost:* medium
  - a4-tok it249 (93% vs SimpleBot on the human lists) or arch-A on the human side vs the walls under the walls' pilot. *Distinct:* Strongest existing human-list pilots, never played against the walls; evaluation only, allowed by rule 1. May not know Snorlax JU or the special Energy. *Cost:* low
  - Stronger human-side-only search (k 8, more determinizations, two-turn horizon on that side). *Distinct:* Same mechanism as #139 with a larger strength step. *Cost:* medium
  - [outside research] Historical 1999-2000 records of Chansey/Snorlax stall vs Haymaker or Wigglytuff. *Distinct:* No in-system pilot nears human level; external evidence on whether the walls are a missing-clock artifact. *Cost:* deep research
- **New hypotheses (section 6):** H76, H87, H100

### H20 · N4, N9 · weakened (moderate) · An independent pilot as judge or drafter moves decks to human types

- **Mechanism:** A frozen pilot that never co-adapted with the walls would judge or draft fairly, so decks would move toward human types.
- **Verdict:** Weak or reward-biased independent judges do not move decks to human types: pilot-v2 (deck-out wins paid 0) as sole drafter (scr-v2, 7 iterations, head never learned) or half-judge (scr-judge2, no gate or type cap) pulled decks toward Pokémon piles, and a frozen human-free scratch pilot did the same across seeds 3-5 (#42-#47). Whether a strong, unbiased independent judge would move decks to human types is untested.
- **Tests:**
  - #34-#36: Frozen deckout-w0 pilot's value as scorer flooded Energy (34 vs 22); value ranked Trainer variants almost in reverse. (refuted (value scorer))
  - #40: Same deck +11 points under the pilot trained on its games. (supports the co-adaptation premise)
  - #42, #43: Frozen human-free scratch pilot judging PSRO search: Pokémon pile with 34+ Energy, almost no Trainers; 'unbiased but weak' (spread 2 vs 18). (refuted (weak judge))
  - #46, #47: Seeds 3-5 under the same frozen pilot: most runs 32-36 Energy; every head mode worse than novelty alone. (refuted (multi-seed))
  - #85, #89: pilot-v2 rates the Trainer-lighter meta higher (iteration 149 with 5 Trainers beat 99). (pilot-v2 not neutral)
  - #131 scr-v2: 7 iterations: median 15/25/21 -> 29/19/12; deck-outs 20% -> 48%; h_in 5.603-5.615 nats (head never learned). (refuted for this configuration (ungated selection noise))
  - #132, #134 scr-judge2: 460-479: median 16-19/15-16/25-27; deck-outs 36% -> 48%; distance 23.7-29.3 vs control scr-reset 19.3/12.3; types never measured. (refuted for this configuration (worse than control))
  - #146: One-turn-search judge on both seats still ranks walls first (0.59). (related (fairer by strength))
  - #147: pilot-v2 rates walls 0.264 vs 0.68-0.75 for population pilots, attributed to deck-out-0 training (#48). (judge biased by reward design)
- **Do not repeat:**
  - PSRO or value-scored deck search under frozen pilot-scratch it249, with or without --head-mode screen/combine/agree or --common-deals (#43, #46, #47, three seeds)
  - Frozen-pilot start-of-game value as deck scorer (--builder value, deckout-w0 pilot, #34-#36)
  - --freeze-pilot pilot-v2 --init-wide --select --candidates 3 without a significance gate (scr-v2, 7 iterations)
  - --judge-pilot pilot-v2 --judge-share 0.5 with --draft-reset from 460, no type cap or gate (scr-judge2)
- **Untested variants:**
  - Frozen independent judge trained on wide random decks with deck-out wins paid 1. *Distinct:* Removes the deck-out-0 confound (#147) so the judge can see the stall plan; coevo-1 (#52) never served as a frozen judge. *Cost:* medium
  - Minimum over judges (population pilot and independent pilot) instead of pooled games. *Distinct:* Blocks a deck winning on the co-adapted pilot's half alone; only greedy-vs-searched minima exist. *Cost:* medium
  - Independent judge with play-time search (pilot-v2 plus one-turn psearch). *Distinct:* --judge-search uses the population's own pilot; strong and non-co-adapted together is untested. *Cost:* medium
  - Frozen pilot-v2 judge with --select-z 1.0 --candidates 1, type cap and turnover every 5. *Distinct:* scr-v2 and scr-judge2 lacked these, so their drift is partly F3 noise. *Cost:* medium
  - Frozen more-general population pilot (scr-anchor or scr-resetent) as judge in a screen. *Distinct:* Static judge already 0.69-0.73 (#147), so predicted to fail; untested as a screen. *Cost:* medium (low value)
  - PFSP-style pool of several frozen past pilots as judges. *Distinct:* Averages over several pilots' biases; dropped from the #138 design, never run. *Cost:* medium
  - [outside research] Building a strong independent evaluator without human data. *Distinct:* No in-system judge is both strong and unbiased; beyond the #144 coverage. *Cost:* deep research
- **New hypotheses (section 6):** H76, H86, H90, H100, H107, H108

### H21 · N4 · refuted (moderate) · Greedy judging fixes the shape

- **Mechanism:** Sampled follow-through erases the value of Trainer timing, so a greedy judge should rank Trainer-rich decks higher; in practice the judge's pilot, not its sampling temperature, decides the verdict.
- **Verdict:** Refuted only narrowly: under a pilot adapted to the walls, greedy judging scores the walls almost the same as sampled judging (0.4957 vs 0.4922 within the wall type at seg_0460), and greedy judges still rate the walls 0.70-0.73 against the human lists (0.60 with a 60-turn limit). The prediction that greedy judging favours Trainer-rich types was never tested: every deck probed was a wall, and the two 460 screens ran one iteration with the collapsed head, which leaves them inconclusive.
- **Tests:**
  - #129 (runs/probe/judge_probe.log): 3 best 360 vs 3 best 460 walls, pilot seg_0460, 576 games/mode: greedy 0.4957, sampled 0.4922, same per-deck order; endings prizes 356/deck-out 140 vs 266/215 (refuted within the wall type only)
  - #128, #129 (scr-judge, scr-judge-select): Ran 460->461 only, stopped on the probe's reading; inherited head at 0.07-0.18 nats, no floor/group; scr-judge had no --select (ratchet) (inconclusive (killed early, confounded))
  - #127: Greedy probe under main pilot at 450: walls 0.784-0.826 vs human lists; greedy pilot-v2 0.253-0.263; sampled 0.832 at 460 (#129) is unpaired (judge's pilot decides, not greediness)
  - #139, #146, #147: Greedy judge 0.706-0.734 vs search both seats 0.573-0.592; greedy with 60-turn draw limit still 0.60 (greedy judging alone does not flip the verdict)
  - #79, #80: Greedy follow-through raises Trainer timing value: pilot-v2 +0.97 vs +0.52 sampled; it79 base +1.32 vs +0.35 (origin of the mechanism (decision level))
  - #81, #82: --explore 0.1 mostly greedy PPO collection: -61 Elo from start, -116 vs unchanged; less sampling, fewer Trainers played (refuted on the training side)
  - #62: Greedy play finds free cycles in 25% of games vs 0.5% of training games (known stall risk of greedy judging)
  - unlogged (#148 build): scr-t60gate479: Greedy judging + --max-turns 60 + --select-z 1.0 from 479, ran 480-498 (EPIPE crash): largest type 40 at 494, 70/99 Chansey+Snorlax (greedy + limit + gate does not hold type)
- **Do not repeat:**
  - --judge-explore 0 without --select from main seg_0460 with the inherited collapsed head (scr-judge)
  - --judge-explore 0 --select --candidates 3 from main seg_0460 with the inherited collapsed head (scr-judge-select)
  - Greedy-vs-sampled block probe within one type (best walls of one population vs another) under the population pilot (judge_probe.sh)
  - Greedy judging with --max-turns 60 as the lever, offline (walls still 0.60 vs the human lists, #147)
  - Greedy judge + --max-turns 60 + --select-z 1.0 --candidates 1 from scr-resetcap 479 (scr-t60gate479)
  - --explore 0.1 mostly greedy PPO collection (#81-#82)
- **Untested variants:**
  - Greedy judging (no turn limit) under the later drafting recipe: draft reset, 3-nat floor, group changes, significance gate. *Distinct:* The 460 screens had a collapsed head and the forced-swap ratchet; scr-t60gate479 adds a 60-turn limit, so greedy judging alone in the later recipe is unread. *Cost:* 1 screen, 20-30 iterations
  - Pilot-v2 as a greedy judge in training. *Distinct:* Separates greediness from a wall-adapted judge; scr-judge2 used pilot-v2 with sampled judge games, and #127's greedy pilot-v2 probe was evaluation only (#127/#147 suggest the pilot dominates). *Cost:* 1 screen
  - Paired greedy-vs-sampled run of walls against the 24 human lists, same pilot and same deals. *Distinct:* Settles the unpaired 0.784-0.826 (#127, pilot 450) vs 0.832 (#129, pilot 460) comparison. *Cost:* low (offline probe)
  - Low-temperature or small-epsilon judging (0 < e < 1). *Distinct:* Only e=0 was tried; the mechanism differs little from greedy, so low priority. *Cost:* 1 screen
- **New hypotheses (section 6):** H81

### H22 · N4, N2 · weakened (moderate) · A search-strength judge alone flips the verdict

- **Mechanism:** If judge strength is the lever, search-strength play on both seats should win the prize race for the human lists and rank them above the walls; psearch over a biased population value fixes the network's own misplays rather than adding general strength.
- **Verdict:** One-turn psearch k4 dets4 on both seats (3 scr-resetcap 499 walls vs 8 one-per-archetype lists) lowers the walls from 0.706 to 0.573 [0.469, 0.677] but not below 0.5, so search alone does not flip the verdict in that setting. The two-turn arm (96 games, 4 per pair) is underpowered rather than a refutation, and both arms search over the population pilot's own value with a 1-2 turn horizon that cannot reach the walls' deck-out ending at a median 61-66 turns, so this is not a clean test of judge strength.
- **Tests:**
  - #145-#147 (wvh_psearch_both_g0-7.jsonl): One-turn k4 dets4 both seats, 8 games/pair, 192 deals: 0.573 [0.469, 0.677] vs greedy 0.706; paired -0.133 [-0.227, -0.047]; walls' 110 wins: 83 deck-out (not supported (CI includes 0.5))
  - #146: Interim one-turn both seats at 152 games: 0.592 vs greedy 0.734 (not supported)
  - #147; unlogged wvh_psearch_both_h2_g0-3.summary.json: Two-turn both seats, 4 games/pair, 96 games: 0.5833 +/- 0.0986; same deals one-turn 0.5625, greedy 0.755; paired +0.021, SE 0.059. #147 at 49 games: 0.571 vs 0.531 (inconclusive (underpowered))
  - #139: One-turn search on human side only, same deals: 0.578 [0.484, 0.677] vs greedy 0.706; paired -0.128; STS round rule 0.40-0.49 (same as both seats)
  - #147: Search both seats plus draws at T 50/60: 0.440-0.458; two-turn file re-scored 0.474/0.464 vs one-turn 0.448/0.484 on same 96 deals (flip needs the draw limit; depth adds nothing)
  - #147: Greedy-judge sweep over 10 population pilots 0.676-0.746 vs pilot-v2 0.264 (judge identity moves the verdict more than search)
  - #50: psearch k4 dets4 over pilot-v2 beats its own greedy pilot 65.4% but not SimpleBot (82.5 vs 81.7%) (search gain is self-referential (confound))
  - #96: Puzzles k4 vs k8: 89.0% vs 90.2% overall; Trainer-first 84.5% vs 87.6% (raising k worth about 1 point)
  - #139/#147 re-weighting (verifier): Weighted by list frequency: 0.462 human-side search, 0.543 one-turn both, 0.510 two-turn; subset Wigglytuff list greedy 0.40 vs 0.71 over all 10 (headline depends on list sample)
  - #13: Flat Monte Carlo, heuristic rollouts, 2-turn horizon: 25% vs the heuristic (shallow determinized search weak in this engine)
- **Do not repeat:**
  - walls_vs_humans psearch k4 dets4 h1 on both seats, 3 resetcap499 walls vs 8-list subset, 8 games/pair (#145-#147)
  - walls_vs_humans psearch k4 dets4 h2 on both seats, same walls and subset, 4 games/pair, 96 games (unlogged)
  - walls_vs_humans psearch k4 dets4 h1 on the human side only, seed 11, stride 32, 8-list subset (#139)
  - walls_vs_humans with nodraw:15 on the human side over all 24 lists (#141)
  - Greedy-judge sweeps over further population pilots (scr-* checkpoints) judging the 3 resetcap499 walls vs 24 lists (#147: 0.68-0.75)
  - Post-hoc draw-at-T re-scoring of the existing wvh_* runs (#139/#147; two-turn file 0.469/0.474/0.464/0.521 at T 40/50/60/70)
  - Building or screening search-strength judging at one-turn k4 dets4 as the only change, with no draw limit (#146 declined it)
- **Untested variants:**
  - Search whose leaf value is not the population pilot's (pilot-v2's network or full-game rollouts), paired design. *Distinct:* Separates judge strength from the judge's own bias, which #50 says psearch over the same network cannot do. *Cost:* medium
  - Horizon or leaf evaluation that reaches the game end: full-game rollouts or information-set MCTS. *Distinct:* The walls' edge is a deck-out ~60 turns out that a 1-2 turn horizon cannot see; outside research on strategy fusion in determinized search over long stall games applies only if this still ranks the walls first. *Cost:* high
  - psearch on the walls' side only. *Distinct:* Decomposes both-seats (0.573) vs human-side (0.578): whether search helps the walls at all is unmeasured. *Cost:* low
  - All 24 lists or frequency weighting, with at least 2 wall sets. *Distinct:* Only resetcap499's 3 walls and one list per archetype were used; weighting moves the headline by up to 0.12. *Cost:* low-medium
  - 8-16 determinizations, k 8 on the walls evaluation. *Distinct:* Never varied (all runs dets 4, k8 only in #96 puzzles); reduces re-deal noise but extends neither horizon nor changes the value, so expected value is low. *Cost:* low
- **New hypotheses (section 6):** H72, H76, H79, H81, H82, H85, H88

### H23 · N4, N1, N5 · inconclusive (weak) · Search judging plus a 50-60 turn draw changes what the loop selects

- **Mechanism:** The walls win only through weak prize-race play and the clockless long game, so a judge that plays at search strength and draws long games should stop paying them.
- **Verdict:** Offline, search on both seats with draws at T=50/60 puts the walls at 0.440/0.458, but that is a post-hoc truncation re-score of 192 games with intervals including 0.5. The one in-loop screen (scr-jsearch479: --judge-search 200, score min, prior 4, z 1.5, --max-turns 60, --select-z 1.0 from 479) did not move the population off Chansey/Snorlax (76/99 at 494), yet its searched games flipped selection no more often than noise, so the mechanism has not had a powered test.
- **Tests:**
  - #147: Offline search both seats, unlimited games re-scored as draws past T=50/60: 0.440/0.458 (greedy at 60: 0.604); 3 walls x 8 lists, intervals about +/-0.10 (weak support (not significant))
  - unlogged (#148): scr-jsearch479: 480-496: median 10/28/22 -> 13/25-26/20; largest type 8->22->39 at 484/489/494; C+S 76/99 at 494; select_flips 0-2/iteration vs null 0.05-2.9 (inconclusive (searched games inert))
  - unlogged: scr-t60gate479 and matched arms at 494: Greedy + --max-turns 60 + gate, 480-498 (EPIPE): largest type 40, C+S 70, median 12/27/20; scr-gate479 66, scr-ctl479 84 C+S (limit with greedy gate does not hold type; search added nothing)
  - #139: Search on human side, STS round rule (more Prizes 2/3, tie draw): walls 0.400/0.426/0.486 at cuts 40/50/60 (offline support for a Prize-tiebreak clock)
  - #140, #142, #143: Greedy plain-draw limits from 479: 40 turns, 94% of games end at limit by 489-491; 70 and 120 relapse to one type within 15 iterations (limit alone fails)
  - #146: One-turn search both seats, 152 games: 0.592 vs greedy 0.734 (search alone does not flip)
- **Do not repeat:**
  - --judge-search 200 --judge-score min --judge-search-prior 4 --judge-search-z 1.5 --max-turns 60 --select-z 1.0 --candidates 1 from scr-resetcap 479 (scr-jsearch479)
  - Greedy judge + --max-turns 60 + --select-z 1.0 from 479 (scr-t60gate479, 480-498)
  - Greedy-judge plain-draw turn limits 40/70/120 from 479 (#140-#143)
  - Offline one-turn psearch k4 dets4 on both seats without a limit as a test of search alone (#146-#147)
- **Untested variants:**
  - --judge-score search (a search-only judge) with --max-turns 60. *Distinct:* The min rule can only demote decks from their greedy score; #147's offline flip came from a search-only judge. *Cost:* 1 screen
  - Powered searched share: --judge-search 1000+ or all judge games, --judge-search-prior about 1, z about 0.5; success = select_flips well above flips_null. *Distinct:* At 200 searched games (about 13% of 1,494, ~2 per candidate) the searched signal was below noise, so any null result is uninformative. *Cost:* 1 screen at a higher per-iteration cost (not measured)
  - Search judging without the limit in the loop (--judge-search with --max-turns 0). *Distinct:* Factorial control to attribute effects; offline search alone gives 0.573-0.592, so expected to fail. *Cost:* 1 screen
  - STS round rule in training (Prize count decides unfinished games, 2/3 vs 1/3, tie a draw) instead of a plain draw. *Distinct:* Puts the margin into the payoff only for long games; #139 offline 0.40-0.49; Evan chose plain draws in #140, so needs his approval. *Cost:* 1 screen plus a small engine change
  - Outside research on evaluation-only search budgets and their ranking correlation. *Distinct:* Only if a powered search-only judge still keeps the walls; #144 already covered Gumbel, SPARTA and KataGo. *Cost:* research pass
- **New hypotheses (section 6):** H72, H82, H84, H89, H90, H102, H103, H107

## N5 · Selection statistics

### H24 · N5 · established (moderate) · Selection noise and the winner's curse

- **Mechanism:** Score noise matches one-card effects, so adopting the best of several noisy candidates accepts non-improvements; it accelerates the biased-judge drift rather than causing it.
- **Verdict:** Established that judging noise is the size of one-card effects and that ungated best-of-3 --select moves decks at about the pure-noise rate (65-83 of 99 per iteration at ~10 games a candidate). Not shown: that re-tests regress inside the metagame loop (one 24-game smoke), or that noise drives the Energy/walls minimum, since gating cut moves about 75% and decks still drifted to walls, and removing deal noise made value-search decks worse.
- **Tests:**
  - #43: Old value scorer: same-deck SD 0.018-0.026 across batch positions vs one-card swaps 0.022-0.038; deal-position artifact, --common-deals gave 0.013-0.023 (supported (scorer artifact, old builder))
  - #46: Common deals made decks worse at seed 3: base 56.2->43.2, novelty 71.8->50.6 (one seed, scratch pilot) (against noise as cause (noise acted as regularizer))
  - #56: League-2 adopted 10 of 10 on 16 games; two-stage smoke (24 games) re-tested same deck 0.29 then 0.54 (supported (one small smoke))
  - #57: Two-stage check, 96+ games: adoptions 5/5, 4/5, 3/5, 3/5; a finalist 0.33 vs current 0.55; lineages still 0-7 Trainers, 29-36 basic Energy (gate cut adoptions; drift remained)
  - #64: Design calculation: ~1,000 samples to resolve a 3-point effect for one choice (draft-head credit, not selection) (consistent (calculation, not a test))
  - #128, #138, #140: Ungated --candidates 3 at 10.1 games/candidate moved 74, 78, 75, 77, 71, 65 (65-83 over 486-499); smoke moved 63 (supported (matches null rate))
  - #140: Gate (c1, z 1.0, 20.2 games/cand) moved 13-28; distance 9.5 vs 15.7; largest type 23 vs 74; accepted moves +0.7-2.5 Pokemon; C+S 73 vs 79 (drift slowed, direction unchanged)
  - #146: Gate plus challenger practice: distance 9.7 vs gate alone 9.5 (no gain)
- **Do not repeat:**
  - Ungated --select --candidates 3 at about 10 games a candidate from the 479 state (scr-select, scr-ctl479, scr-resetcap; #138, #140)
  - --candidates 1 --select-z 1.0 from scr-resetcap 479, reseed 2 (scr-gate479, #140)
  - Gate z=1 with challenger practice --practice-vs 0.5 --practice-vs-from pop from 479 (scr-gatevs479, #146)
  - League two-stage fresh-game re-test with --confirm-min 96 --adopt-margin 2 (#56-#57)
  - --common-deals in the value-search builder (#43, #46)
- **Untested variants:**
  - Pooled noise-aware acceptance: lower confidence bound, re-evaluate the incumbent, beat its best of the last 5 iterations. *Distinct:* Pools evidence across iterations with the incumbent's running counts instead of a one-shot z test; from the first review (#144, recommendation 4), not new outside research; expected to slow, not reverse, the judge-driven drift. *Cost:* medium
  - Direct test of the prediction: re-score every accepted move on fresh games in the metagame loop. *Distinct:* 'Most moves are noise' is inferred from the move rate, never measured. *Cost:* low
  - Stronger gate: z=2 or more games per candidate. *Distinct:* Only z=1 was run; at z=1 about 16% of null candidates (~16 decks) pass, about the gate's whole move count. *Cost:* 1 screen
  - Gate at 3 candidates and ungated at 1 candidate. *Distinct:* De-confounds candidate count and games per candidate (20.2 vs 10.1) from gating in scr-gate479 vs scr-ctl479. *Cost:* 1 screen each
  - Common random numbers (paired deals) between incumbent and candidate in --select. *Distinct:* #43's common deals were in the value search only. *Cost:* low code + 1 screen
- **New hypotheses (section 6):** H89, H95

### H25 · N5 · partly-supported (moderate) · A significance gate holds shape and type

- **Mechanism:** Moving only on a gain above Z standard errors removes noise-driven moves, which slows drift in shape, but the type drift follows the shared judge's real preference for walls, which a noise gate cannot remove.
- **Verdict:** The shape half holds: three gate arms (scr-gate479 9.5, scr-gatevs479 9.7, scr-t60gate479 7.2 cards off) beat the control (15.6-15.7), and two more seeds of scr-gate479 replicate it (#153: 10.6, 11.7), so it is not reseed 2's luck; all share the scr-resetcap 479 snapshot and head, and the gate is confounded with 1 vs 3 candidates and 20.2 vs 10.1 games a candidate, so the effect cannot be attributed to z. The type half is refuted in every arm: Chansey+Snorlax decks went 53 -> 70-80 (control 79) and the gate's own pilot still rates the walls 0.680.
- **Tests:**
  - #138, #140: scr-gate479 vs scr-ctl479: moved 13-28 vs 65-83; distance 9.5 vs 15.7 (490-499); largest type 23 vs 74 at 499; C+S 73 vs 79; accepted moves +0.7-2.5 Pokemon, -0.2-1.9 Trainers (shape supported, type refuted)
  - draft #148 (scratchpad entry148.md, not in progress-log): scr-gate479 C+S 53 (479) -> 54/63/66/73 (484-499) (type not held)
  - #143, #146; scr-gatevs479 log.jsonl: Gate + challenger practice: distance 9.7 vs 9.5; C+S 70 vs 73; largest type 21, 28, 38, 36 vs gate alone 15, 12, 26, 23 (484-499) (replicates shape effect and type failure)
  - draft #148: scr-t60gate479: Gate + greedy + --max-turns 60: distance 7.24 (490-498) vs 9.24 gate, 15.59 control; C+S 53, 58, 70, 80 (479-498); largest type 12, 25, 35, 41 (shape held, type not)
  - #147: Gate pilots rate walls 0.680 (scr-gate479) and 0.676 (scr-gatevs479) vs control 0.714, pilot-v2 0.264 (gate does not change the judge's bias)
  - #134, #138: Ungated parent scr-resetcap: distance 7.5 at 487 -> 15-20 by 494-499, largest type 72; gate head entropy 2.08 vs 0.50 (entropy may be a second path for shape)
  - #153 (C29): reseeds 3 and 4 of scr-gate479: distance 10.6, 11.7 (490-499) vs 9.55 seed 2, ungated 15.7, 17.2; gated minus ungated -5.8 [-9.4, -2.3]; wall-core 67, 75 at 499 (seed 2 73), gated minus ungated over 484-499 -18.2 [-29.6, -6.8]; largest type -31.9 [-49.0, -14.8]; walls verdicts 0.743, 0.718 (shape replicated over 3 seeds; type still not held; seed 4's largest type 50 at 499)
- **Do not repeat:**
  - --candidates 1 --select-z 1.0 from scr-resetcap 479, reseeds 2, 3 and 4 (scr-gate479, scr-gate479-s3, scr-gate479-s4)
  - --candidates 1 --select-z 1.0 --practice-games 250 --practice-vs 0.5 --practice-vs-from pop from scr-resetcap 479, reseed 2 (scr-gatevs479)
  - --candidates 1 --select-z 1.0 --judge-explore 0 --max-turns 60 --type-cap 0.5 from scr-resetcap 479, reseed 2 (scr-t60gate479)
  - --candidates 1 --select-z 1.0 --judge-explore 0 --max-turns 60 --judge-search 200 from 479 (scr-jsearch479; in progress, do not relaunch)
- **Untested variants:**
  - Gate with 3 candidates (--candidates 3 --select-z 1.0). *Distinct:* Isolates z against scr-ctl479 with candidate count and ~10.1 games a candidate matched; no run has select_z > 0 with candidates 3. *Cost:* 1 screen
  - Mirror cell --candidates 1 --select-z 0. *Distinct:* Isolates candidate count and the doubled per-candidate budget. *Cost:* 1 screen
  - z sweep and a second reseed. *Distinct:* Only z 1.0 and reseed 2 were run. *Cost:* 1 screen per cell
  - Gate from 460 or with --draft-reset. *Distinct:* Proposed in #138/#140 Next, never run; the 479 head is already narrowing. *Cost:* 1 screen
  - Pooled lower-confidence-bound acceptance across iterations (#144). *Distinct:* Re-evaluates the incumbent and pools evidence over time against the optimizer's curse, not a one-shot z test. *Cost:* medium
  - Note on ranking. *Distinct:* All gate variants control noise; the type drift is judge-driven (#147: 0.68), so they refine shape only and rank low; holding type needs a different judge (draft #148 names outside research if scr-jsearch479 also fails). *Cost:* n/a
- **New hypotheses (section 6):** H73, H89, H95, H98, H111

### H26 · N5, N6 · refuted (moderate) · Forced-move ratchet; move only when better (--select)

- **Mechanism:** Decks forced to a new draw every iteration walk downhill, and with no copy limit on basic Energy, null Energy-for-Energy swaps pile up; accepting only better draws should stop this, but the shared judge's accepted moves still add Pokemon and Energy.
- **Verdict:** Plain --select --candidates 3 does not stop the Energy pile-up: from the 479 state with a reset or carried head it relapses to median Energy 27 and one type of 74 within 20 iterations (scr-resetcap, scr-ctl479), and earlier accept-if-better drafting (league #56-#63, value search #43) also drifted into piles. The forced-move ratchet remains a plausible contributor on the #127 correlation alone, the old-head scr-select screen (6 iterations, Energy never logged) is underpowered, and the runs that held Energy down did it through the entropy floor or the confounded --select-z gate, not --select itself.
- **Tests:**
  - #66: meta-dev forced moves (3 agents, no population): a0 46->25 basic Energy by it10, then 9/21/30, 22/14/24, 50/4/6 at 110, 3/53/4 at end (supported for downhill walk only)
  - #127: 87-97% Energy-for-Energy moves at 448-449; best-deck median Energy 22 (360) -> 28 (400) -> 37 (440); basic Energy favourite only from ~440 (supported correlationally (last stretch))
  - #127, #128: 019 select cards killed by the 23:05 shutdown, never relaunched (underpowered)
  - #128-#130 (scr-select): Old head 0.07-0.18 nats: distance 36.0, 36.0, 36.0, 35.8, 38.5, 37.2, 37.3 over 460-466; Energy not logged; stopped partly for RAM (inconclusive (underpowered, confounded))
  - #128, #129 (scr-judge-select): --select --candidates 3 --judge-explore 0 old head: 37.3 -> 37.3 over 460-461 (inconclusive)
  - #130, #131: Old head + select + floor 3 + group 0.3: scr-draft 31.0->26.0 (460-465); scr-practice median Energy 36->28-29, distance 18.8-23.7, deck-outs 40-49% (select moves once candidates diverse)
  - #134, #135, #140, #145: scr-resetcap/scr-ctl479 plain --select c3: median 10/28/22 at 479-481 -> 13/20/27 at 499; distance 7.5->20.7 by 497; largest type 74 (refuted)
  - #138, #140: scr-gate479 (--select-z 1.0, c1): median 13/25/21 vs control 13/20/27; accepted moves +0.7-2.5 Pokemon; 73/99 C+S (different mechanism, confounded)
  - #56-#63: League two-stage adoption check (--adopt-margin 2): decks ended 29.0 Pokemon / 5.3 Trainers / 24.1 basic + 1.5 special Energy (accept-if-better did not prevent piles)
  - #43: Greedy value search (accept if pilot value improves): Pokemon pile with 34+ Energy, almost no Trainers (pile-up without forced moves)
  - #131, #132: With --select from wide decks: scr-v2 Pokemon 15->23; scr-scratch 12->25 (select does not stop pile drift from scratch)
- **Do not repeat:**
  - --select --candidates 3 with the old collapsed head from 460 (scr-select)
  - --select --candidates 3 --judge-explore 0 with the old head from 460 (scr-judge-select)
  - --select --candidates 3, ungated, with a reset or the 479 head from the 479 state (scr-resetcap, scr-ctl479)
  - Accept-if-better drafting on the pilot's value estimate (value search #36-#43)
  - Two-stage real-game adoption check with a fixed margin as the only guard against pile drift (league #56-#63)
- **Untested variants:**
  - Forced moves (no --select) with a reset head + 3-nat floor + group 0.3, against scr-reset. *Distinct:* Every screen that moved the shape had --select; whether select matters once candidates are diverse was never isolated. *Cost:* 1 screen from 460
  - --select-z 1.0 with --candidates 3 (or a plain --candidates 1 control). *Distinct:* The gate pair changed gate and candidate count together. *Cost:* 1 screen from 479
  - Log Energy/Trainer counts of accepted vs rejected moves in a plain --select run. *Distinct:* Tests the ratchet claim directly (are accepted moves Energy-adding?); acc/prop fields exist since #138. *Cost:* analysis only, scr-ctl479 log
  - Pooled noise-aware acceptance (LCB, re-evaluate incumbent, beat its best of last 5). *Distinct:* Re-scores the incumbent across iterations against the optimizer's curse (#56); listed by #144. *Cost:* medium
  - --draft-group-p alone. *Distinct:* Never ablated (always with floor 3), but it concerns draft-move granularity and copy limits, so it belongs with the drafting-operator family (H28/H30), not H26. *Cost:* 1 screen
- **New hypotheses (section 6):** H94

## N6 · Draft operator

### H27 · N6 · supported (moderate) · Proposal base rates pull decks toward Pokemon piles

- **Mechanism:** 225 of 277 cards are Pokemon, so near-uniform proposals add mostly Pokemon, often orphan evolutions, and a pilot that values Trainers little or rewards deck-outs accepts them.
- **Verdict:** Supported as a descriptive proposal-side pull: the pool is 81% Pokemon per uniform draw, and near-uniform heads drift to Pokemon-heavy decks in at least six runs, most cleanly in #125's zero-signal exploiters (29/17/13 and 37/11/12 by 429). Its causal role in the walls or pile minima is untested: 'regardless of results' is shown only under forced moves or zero signal, no kind-balanced ablation exists, and #109 shows a second, low-entropy route to Pokemon drift.
- **Tests:**
  - #63: Old card-id swap operator with real-game check: 29.0 Pokemon / 5.3 Trainers / 24.1 basic + 1.5 special Energy; 31.6% of Pokemon copies orphan evolutions (supported (base rate plus results))
  - #124: Pool 277: 225 Pokemon, 42 Trainers, 6 basic, 4 special Energy; uniform draw 81% Pokemon, 2% basic Energy; scratch 22->59 Pokemon with non-attacking pilot (supported arithmetic; drift confounded)
  - #120: Fresh heads at ~5.6 nats after one iteration: 13/21/26 and 12/22/25 vs head 0's 8/23/28 (supported)
  - #121, #123: Fresh league heads, forced moves, no --select: 23/19/18 and 24/19/16 at 405; 26/16/17 and 34/15/11 at 409 (supported (with forced-move ratchet))
  - #125: Fresh exploiters at 5.41-5.58 nats, z 0.02-0.05 vs head 0: 29/17/13 and 37/11/12 by 429; learning heads (1.70-2.24 nats) returned to 8/24/27 (supported (cleanest regardless-of-results case))
  - #131: scr-reset median Pokemon 8->17 by 468; scr-v2 (frozen pilot-v2, wide decks, --select) 15->18->20->23 in 4 iterations (supported)
  - #132: scr-scratch (gamma 0.995): Pokemon 12->25, deck-outs 61%->85% in 4 iterations (supported (confounded with non-attacking pilot))
  - #140: Gate at 2.08 nats: accepted moves +0.7-2.5 Pokemon, -0.2-1.9 Trainers, close to proposals (pull survives selection via judge)
  - #109, #112: Main line 10/29/20 -> 33/8/20 in 13 iterations at 0.09-0.32 nats, Snorlax 0.9999; sister fork did not drift (counterexample: second route)
  - DATA (scratchpad ledger only): Distance by head entropy: 18.1 at >=2.5 nats, 13.4 at 1.5-2.5, 16.3 at 0.5-1.5, 25.8 below 0.5 (not applicable (confounded, measures distance not Pokemon drift))
- **Do not repeat:**
  - Fresh (uniform) exploiter heads rewarded only against a strong head 0 (018-meta-league3-exploit, #125)
  - Fresh draft heads with forced per-iteration moves and no --select in a league (017-meta-league3-m fresh, #121-#125)
  - From-scratch recipe with a near-uniform head and a non-attacking pilot (016-scratch-recipe-m #124; scr-scratch with gamma 0.995 #132)
  - Frozen pilot-v2 drafting from wide decks with --select (scr-v2, #131)
- **Untested variants:**
  - Kind-stratified proposals (pick kind, then card) or kind-balanced initialisation of the head's per-card bias b_in, at a fresh head with and without --select. *Distinct:* Removes the proposal prior without touching results; proposed in #63 Next, never built; game-agnostic, but a fixed operator needs a rule-3 check with Evan (b_in init is the rule-compatible form). *Cost:* low
  - Entropy floor or uniform exploration only on draws that count for the draft head, not on decks the pilot trains on. *Distinct:* Separates exploratory base-rate drift from the population's real decks (#115 Next, not built). *Cost:* small code + 1 screen
  - Measure the orphan-evolution rate of learned-head decks. *Distinct:* Never measured after #63's 31.6%; cheap check whether the dead-card pull still applies. *Cost:* analysis only
  - Whole-line adds, or generally adding cards the card's rules text references. *Distinct:* Line-structured starts alone did not stop drift (scr-v2 15->23); evolution lines are Pokemon-specific and may fail rule 2, so the rules-text form is needed for MTG. *Cost:* low-medium
- **New hypotheses (section 6):** H92, H97, H109, H110

### H28 · N6 · adopted (weak) · Changes per draw: learned rate vs fixed 3 vs 6

**Evan:** his idea (rule 4: tried first and fully).

- **Mechanism:** The number of changes per draw sets reach and stability; a learned rate follows any correlation between changes and reward and Adam can drive it to zero, while a large fixed count under forced moves amplifies null swaps.
- **Verdict:** --swaps 6 has been in main_args since #91 on one fork scored under the main line's own pilot (+0.128 answer key, pilot gate +2.8 Elo [-8.3, 13.9]), and #127 later shows 6 forced changes per draw fed the Energy ratchet. The learned change rate is refuted only for REINFORCE with no rate floor, forced moves, no selection and N=3 agents (#66, and #67 with margin 0.5); no change count has been compared under --select or --select-z.
- **Tests:**
  - #65: Synthetic bandit paying any hit: rate rose to ~56 cards a draw (diagnostic (rate follows change-reward correlation))
  - #66: meta-dev learned rate: a1 2.9->0.01, a2 2.9->0.08, a0 rose 3.1->6.3 (max 6.7); vs human lists 0.00/0.02/0.23 under pilot-v2 (refuted (pre-selection, forced moves, N=3))
  - #67: meta-dev-c with margin 0.5: rate under 0.5 at it15 (a1), it40 (a0), it43 (a2); ended 0.76/0.00/0.00; stopped at 84 of 150 (refuted (learned rate plus margin))
  - #91: 6 vs 3 swaps from 200: answer key 0.823 vs 0.695 (+0.128); best deck 0.861 vs 0.822; staples 3.83 vs 2.25; gate +2.8 Elo [-8.3, 13.9]; main collapsing 0.794->0.695 (adopted (one fork, confounded))
  - #92: Under 3 swaps main line fell to median 2 Trainers at 216, 16 of 99 decks with none (baseline of #91's gain)
  - #86: Found 4: each deck takes one sampled 3-card draw an iteration; population median swings over tens of iterations (fixed count under forced moves tracks the head)
  - #127: 6 forced changes + one-card incoming choice: 87-97% Energy-for-Energy, 36.5 Energy; group changes gave 9.36 cards changed a draw from 3 changes (against 6 swaps under forced moves)
  - #130, #132: Select + 3-nat floor + group 0.3 moved the shape (reset screens 11-14 cards off); edit size bundled with the floor (edit size never isolated)
- **Do not repeat:**
  - Learned per-copy change rate trained by REINFORCE with no floor, decks forced to move to every draw, N=3 agents (#66; #67 with --draft-margin 0.5)
  - A bandit that pays any hit, used to test a change rate (#65)
  - --swaps 6 vs 3 judged by the answer key under the main line's own pilot against a main line in mid-collapse, one fork from 200 (#91)
  - Any fixed --swaps value without --select (forced moves every iteration form the #127 ratchet)
- **Untested variants:**
  - Learned change rate under --select or --select-z with a floor on the rate (minimum expected changes or entropy floor on the count). *Distinct:* The learned rate was removed in #67 before selection existed; selection removes the 'walk downhill' failure #66 named. *Cost:* small code + 1 screen
  - --swaps 3 vs 6 vs 10-12 under --select or --select-z. *Distinct:* Only 3 and 6 were ever run, and only under forced moves (#91). *Cost:* 1 screen per arm
  - --draft-group-p 0 vs 0.3 with the 3-nat floor held fixed. *Distinct:* Group changes always arrived bundled with the floor (#127, #130, #132). *Cost:* 1 screen
  - Non-learned adaptive count by selection's acceptance rate (ES-style success rule). *Distinct:* Feedback on step size rather than REINFORCE on the count; game-agnostic and Occam-compatible; no grep hits; outside literature (ES success rules, MAP-Elites operators) only if in-system arms come back flat. *Cost:* small code + 1 screen
  - Fine-tune the pilot on a new deck before judging large edits. *Distinct:* Large edits are judged by a pilot that has not practised them; seasons (#93) are a partial earlier attempt and must be cited. *Cost:* medium
  - Assess the edit size of turnover mutants (10 random cards, random_changes). *Distinct:* A fixed large-edit operator running since #67, never assessed. *Cost:* analysis only
- **New hypotheses (section 6):** H97

### H29 · N6 · adopted (weak) · Prize margin in the draft reward

**Evan:** his idea (rule 4: tried first and fully).

- **Mechanism:** The prize margin gives a gradient inside all-loss matchups and penalises deck-out wins taken while behind on Prizes, which is the walls' later win route.
- **Verdict:** Result-only draft reward was adopted at 240 on simplicity after a pilot noninferiority test (+0.0 [-11.3, 11.3]), not on drafting evidence; its one answer-key reading was +0.018 (weakly positive, under the main pilot). The claim that margin prevents freezing was refuted only once per arm in the obsolete 3-agent learned-rate design (#67), and margin was never tried above 0.5, where it never reverses a result, so the family is not closed.
- **Tests:**
  - #66: Margin 0.5 introduced (Evan's choice); smoke deck-out-heavy winner mean margin -0.31; at 0.5 the margin never reverses a result (context)
  - #67: meta-dev-c margin 0.5: froze sooner, a1 15 (38 in #66), a0 40 (never), a2 43 (119); a1 mean margin -0.2 to -0.57; n=1 per arm (refuted (obsolete learned-rate design))
  - #91: Main line on margin 0.5 fell to 2-3 Trainers at 220, 16-17 decks with none; walls held from 160 under margin (margin did not prevent collapse)
  - #90: Result-only answer key 0.812 vs 0.794 (+0.018, below 0.03 rule, ~3.6x A/A RMS 0.005); pilot +29.6 Elo [18.6, 40.7]; Energy 29.9 vs 30.0 (inconclusive (weakly positive))
  - #97: 006-meta-margin0-n: pilot +0.0 [-11.3, 11.3] over 1,600 games; archived gate -13.2 [-30.3, 3.8]; adopted at 240 (adopted (pilot noninferiority only))
  - #104: Replication branch fell to 6-7 Trainers at 230-235; post-240 Trainers 7->22 not credited to the reward (neutral or against)
  - #139: Evaluation only, STS round rule (more Prizes 2/3, tie draw) with search on human side: walls 0.40-0.49 (prize-margin term matters to ground truth)
- **Do not repeat:**
  - --draft-margin 0.5 in the 3-agent learned-change-rate setup (meta-dev-c, #66/#67)
  - --draft-margin 0 vs 0.5 judged by a pilot noninferiority test alone (006-meta-margin0-n, #97)
  - --draft-margin 0 vs 0.5 judged on the answer key under the main line's own pilot, one fork per arm (006-meta-margin0, #90)
  - Turn-limit draws with no Prize tiebreak at 40/70/120 turns (#140)
- **Untested variants:**
  - Margin-dominant draft reward (weight 1 or more, or margin alone). *Distinct:* Every test used 0.5, which never reverses a result; a dominant margin scores deck-out wins behind on Prizes below Prize wins. *Cost:* 1 screen
  - Prize margin in the pilot's PPO reward (#124 remedy b). *Distinct:* Acts on play and the co-adapted judge (F2); differs from potential-based prize shaping and from 'lasting shaping' (#106, -31 Elo), which paid in-game prize-taking. *Cost:* 1 screen
  - STS round rule in training: turn limit where the Prize count decides (2/3 vs 1/3, tie a draw). *Distinct:* Puts the margin into the payoff only for long games, where the walls' edge sits; #140 built only plain draws; needs Evan's approval. *Cost:* 1 screen plus small engine change
  - Margin as a judging or selection statistic for --select / --select-z (results plus margin). *Distinct:* Changes which deck is accepted rather than the REINFORCE reward; not in the log. *Cost:* small code + 1 screen
- **New hypotheses (section 6):** H84, H102, H104

### H30 · N6 · partly-supported (moderate) · The head's incoming choice collapses and the population follows

- **Mechanism:** REINFORCE with Adam turns a weak consistent push into a one-card incoming softmax whose entropy gradient then vanishes; this amplifies, but on present evidence does not cause, the judge-driven drift to one type.
- **Verdict:** Established: the REINFORCE head's own incoming softmax collapses to 0.05-0.3 nats onto one card at a time, replicated on the main line, league copies and every reset screen. Only partly supported and confounded: that the population follows, since lag evidence comes from screens with a 3-nat sampling floor forked from an ~87% wall population, populations converge with the head at 2-5.6 nats (#124, #125, #137, #140), and no run tests the stated cause (Adam on noisy results).
- **Tests:**
  - #92: Main head 0.2-1.1 nats vs ~6 uniform; median Trainers 5/15/6/12/2 over 150-216; basic Energy top-3 mass 0.91-0.93 at 210-215 (supported)
  - #109: 0.09-0.32 nats over 296-319 (uniform ~5.6); Snorlax 0.9999; Oak -2.86, Bill -3.16 cards/deck 289->319; dual-ascent weight 36, entropy 0 (supported)
  - #120, #121, #125: Bias <=0.13 (s.d. 0.02), context weight norm 5.10 at 400; copies h_in 0.02-0.17 drafting 8/23-24/28-29; at 429 all heads 8/23/28, h_in 0.05-0.06 (supported (copies alike))
  - #127: Top-card share 0.56-0.98 over 300-449 (Bill 0.97 at 300, Lightning 0.97 at 449); h_in 0.13-0.27 at 438-447; plus forced-move ratchet and Energy copy limit (supported (with ratchet))
  - #130: scr-typecap, old head 0.05-0.2 nats: turnover decks joined the main type within 5 iterations (supported)
  - scr-reset, scr-gamma run logs: h_in <1 at 479/480; largest type 41 at 489, 61 at 491 (lag 10-12); 39 at 489, 72 at 499 (lag 9-19); draws floored at 3 nats (confounded)
  - #134, #135: scr-resetcap: 7.5-10 cards off while h_in 3.1-2.6; h_in 1.1->0.56 as largest type 9->72, distance 15-20 (supported (best paired evidence))
  - #136, #137: scr-resetent (--draft-ent 0.05): h_in 3.78-5.60; C+S 59 (469), 62, 83, 89 (496); Trainers 13-16; overlap largest type 23 (against necessity of collapse)
  - #124: From scratch head 5.60->5.22 nats, population collapsed to 59/1/0 Pokemon piles (counterexample)
  - #138, #140: Gate h_in 2.08 vs 0.50; largest type 15-26 vs 33-74; C+S 73 vs 79; proposals added Trainers, accepted moves added Pokemon (selection and judge drive type)
  - #67: Adam drove change rate 3->0.01 in ~30 iterations from correlation -0.01 to -0.03; bandit target mass 0.029->1.000 in 200 steps (supports Adam amplification (change rate))
  - #112, #113: Two forks of 300 diverged within 12 iterations (8 vs 23-29 Trainers); under 2-nat floor head entropy still 0.41->0.06 (collapse stochastic; floor acts only at sampling)
  - #115, #118: 3-nat floor Trainer range 3 vs 8 main, 10 at 2 nats, -27 to -33 Elo, both failed; draft lr 3e-4 range 4 vs 5 (fixes did not hold)
  - #143, #146: h_in 1.01 (turns70), 0.53 (turns120) with relapse; copied exploiters at even terms drafted the same walls (supported)
- **Do not repeat:**
  - Dual-ascent or extra-weight entropy bonus on an already collapsed head (#109)
  - Incoming-entropy floor of 2 nats at sampling on the main line (#109/#115)
  - Incoming-entropy floor of 3 nats at sampling applied to both counted and PPO decks (#115)
  - Entropy bonus x5 (--draft-ent 0.05) on a reset head with selection, floor, group changes and type cap from the 460 walls (scr-resetent, #134-#137)
  - --draft-reset with selection, 3-nat floor and group changes from the 460 walls population (scr-reset, scr-gamma, scr-resetcap; #130-#135)
  - Slower draft lr 3e-4 as a stability fix (#118)
  - League of 3 draft heads sharing the pilot, copies or fresh (#120-#125)
  - Exploiter heads, fresh (#123-#125) or copied (#143/#146)
- **Untested variants:**
  - Swap the head's optimizer (plain SGD, Adam with larger eps or lower beta2) or add a trust region / KL-to-previous on the head. *Distinct:* The only direct test of the stated 'Adam on noisy results' cause (#67 implicates Adam). *Cost:* low code + 1 screen
  - Floor that applies only to the draws that count for the head, not to decks the pilot trains on. *Distinct:* Separates head exploration from the -27 to -33 Elo pilot cost (#115 Next, never built). *Cost:* small code + 1 screen
  - Reset head started from a diverse population (wide decks under pilot-v2 or an anchored pilot). *Distinct:* Removes the inherited-incumbent confound: every reset screen forked from the ~87% wall 460 state. *Cost:* 1 screen
  - Entropy bonus x10 (--draft-ent 0.1, scr-resetent10). *Distinct:* Untested, not refuted: stopped after 2 iterations for low memory (#136). *Cost:* 1 screen
  - Per-card play-log features on deck tokens. *Distinct:* Per-card credit instead of one result per draw (notes/tcg-rl-research-notes.md:186); targets credit, not collapse, and inherits the judge's bias, so pair it with a fairer judge. *Cost:* medium
  - Outside research on policy-gradient entropy collapse (covariance-driven decline, Clip-Cov / KL-Cov style updates, trust-region or mirror-descent updates for categorical heads). *Distinct:* Not covered by the first review (#144); references not yet verified. *Cost:* research pass
- **New hypotheses (section 6):** H93, H94, H111

### H31 · N6 · refuted (moderate) · Keep the head undecided (entropy bonus)

- **Mechanism:** A near-uniform head drafts at the pool's base rate (225 of 277 cards are Pokemon, so 81% of picks), which pulls decks toward Pokemon piles instead of bringing Trainers back.
- **Verdict:** Refuted as tested. A uniform-reference entropy bonus of 0.05 on a reset REINFORCE head judged by the population's own pilot (scr-resetent, matched to scr-resetcap except draft_ent; partly replicated by scr-anchor) kept the head at 3.8-5.6 nats but made the shape worse: Trainers never above 16, and Chansey+Snorlax decks went from 59 to 89 of 99. What is not shown: a dose of 0.1 or more over a readable span, intermediate entropy (2.5-3 nats), or any arm judged by something other than the walls-biased own pilot (F2).
- **Tests:**
  - #109: Dual ascent on the check_draft bandit (unit test): weight rose to 36, entropy stayed 0; at faster rates entropy flipped between 5.6 and 0 (refuted (mechanistic, on an already collapsed softmax))
  - #134-#137: scr-resetent (--draft-ent 0.05, only draft_ent differs from scr-resetcap): h_in 5.60 -> 3.78-4.21; median Pokemon 8 -> 25 by 471; ends Trainers 13, Energy 28; control reached 28 Trainers (refuted)
  - offline, population_it0469.pt / final.pt: scr-resetent decks with both Chansey and Snorlax 59 (469) -> 62 (479) -> 83 (489) -> 89 (496) of 99; largest overlap type 31 then at most 23 (descriptor artefact) (refuted (computed offline, not a log figure))
  - #135, #138: scr-anchor (--draft-ent 0.05 + KL anchor to pilot-v2, to 472): h_in 5.60 -> 3.58; median Pokemon 8 -> 19; 19/16/25 at 472, as its control (refuted (partly independent arm))
  - #135, #136: scr-resetent10 (--draft-ent 0.1): 2 rows (460, 461), stopped for low memory; scr-practice1k (0.05) 1 row (underpowered)
  - #121, #123, #125: Fresh league heads at 5.3-5.6 nats drafted Pokemon piles and lost (head 2: 34/15/11 at 409, 30/18/11 at 419) (corroborates mechanism)
  - #124: From scratch: incoming entropy 5.60 -> 5.22, collapsed to Pokemon piles 59/1/0 by it 39; pool 81% Pokemon (corroborates mechanism)
  - #134, #135: scr-resetcap: closest shapes 7.5-10 cards off at intermediate entropy 3.1 -> 2.6 nats; relapsed as entropy fell to 1.1 then 0.56 (partly supports an intermediate-entropy story)
  - #109, #115: Related lever (see H32): temperature floor 3 nats held Trainer range to 3 at 27-33 Elo pilot cost; 2-nat floor did nothing (cross-reference)
- **Do not repeat:**
  - --draft-ent 0.05 with --draft-reset on the resetcap recipe (--select --candidates 3 --draft-h-in-floor 3.0 --draft-group-p 0.3 --turnover-wide --protect 20 --type-cap 0.5 --turnover-every 5 --practice-games 250) from main seg_0460, judged by the own pilot (scr-resetent)
  - --draft-ent 0.05 plus --anchor pilot-v2 --anchor-w 0.1 on the same recipe from 460 (scr-anchor, #135/#138)
  - Dual ascent on the incoming entropy (adaptive weight below a floor) on the bandit or a collapsed head (#109)
  - Incoming-entropy temperature floor of 2 nats on the collapsed main line (013-meta-hin2, #115)
  - Fresh near-uniform draft heads in a league without exploiter rules from 400 (017-meta-league3-m, #121-#125)
- **Untested variants:**
  - --draft-ent 0.1 or higher in a population run long enough to read (scr-resetent10 ran 2 iterations). *Distinct:* Dose test only, same mechanism; the 0.1 arm never produced data. *Cost:* low-medium (one screen, 20-30 iterations; memory-limited)
  - Entropy bonus or floor applied only to the draws that count for the draft head, not to the decks the pilot trains on (#115 Next, not built). *Distinct:* Separates draft exploration from the pilot's 27-33 Elo cost. *Cost:* low-medium (build plus one screen)
  - Entropy toward a non-uniform reference (KL to the deck's current card mix, or a prior balanced over game-agnostic card features). *Distinct:* Removes the 81%-Pokemon base-rate pull that defeats uniform entropy; must derive from card features or rules text (rule 2). *Cost:* medium
  - Annealed draft-entropy schedule, high early and decaying. *Distinct:* Only pilot entropy annealing was ever suggested; varies dose over time, so only marginally distinct. *Cost:* low
  - Strong bonus or floor under an unbiased judge (pilot-v2 judging or --judge-search, #148). *Distinct:* Tests whether exploration helps once the F2 judge bias is removed; probably the most informative variant. *Cost:* medium (search judging is slower)
  - 4-4.5-nat temperature floor on a reset head. *Distinct:* Floors 2 and 3 tested; higher only in #109's scratch trial; acts like the dose test and adds little in mechanism. *Cost:* low
- **New hypotheses (section 6):** H93, H94, H110, H111

### H32 · N6 · weakened (weak) · Sampling-time entropy floor

- **Mechanism:** Sampling below-floor choices at a higher temperature keeps the drawn cards varied even after the head's softmax collapses.
- **Verdict:** A sampling floor keeps the drawn choice at the floor while the head's own entropy collapses (bandit, #109), and a 3-nat floor held the median-Trainer range to 3 in one 40-iteration fork (#115). It did not stop relapse in any later floor-on screen under ungated --select (scr-reset, scr-gamma, scr-resetcap, scr-ctl479). The 27-33 Elo pilot cost came from a gate played on one-type populations and is contradicted by floor-on screens whose pilots were at par with pilot-v2 (#137). No matched floor ablation has completed: the 019 pair was killed by a shutdown.
- **Tests:**
  - #109: Bandit, 2-nat floor: every draw >= 2.00 nats while head entropy fell to 0 (log-prob gap 2.6e-6); only 62% of drawn cards were targets vs 100% unfloored (supported (mechanism), with exploitation cost)
  - #113: hin2 interim at 329: median 12/29/20 -> 9/23/28 while head incoming entropy fell 0.41 -> 0.06 (floor acts only at sampling)
  - #115: 013-meta-hin2: Trainer range 10 vs main 8 (320-359); pilot -27.0 Elo [-39.2, -14.8]; answer key 0.814/0.854; failed stability and pilot gate (refuted (confounded gates))
  - #115: 013-meta-hin3: range 3; pilot -33.3 [-45.1, -21.6]; answer key 0.776/0.807 (-0.037 vs -0.03 floor); passed stability, failed answer key and pilot gate (mixed (biased answer key, one-type pilot gate, one fork))
  - #127, #128: 019-meta-select vs 019-meta-select-floor (--select --candidates 3, with/without 3-nat floor): killed by shutdown at 453, never rerun (killed (no result))
  - #130: scr-draft (floor 3 + group 0.3) 31.0 -> 26-29 vs scr-select (neither) 36-38 over 460-465; floor and group changes confounded (inconclusive)
  - #132, #134, #135: Floor-on scr-reset, scr-gamma, scr-resetcap: 36 -> 11-14 cards off, then relapse as head h_in fell 1.02 -> 0.24 and 3.1 -> 0.56; resetcap 7.5 -> 15-20.7 (refuted (steady shape))
  - #137: Floor-on scr-resetent / scr-resetcap pilots vs human lists: pilot-v2 +2.8 and -22.7 Elo, at par or better; field variety tracked pilot loss (contradicts the pilot-cost claim)
  - #140, #143: scr-gate479 vs scr-ctl479, both floor 3: head entropy 2.08 vs 0.50; only gated arm held shape; control re-formed a 74-deck type (the gate, not the floor, steadied)
- **Do not repeat:**
  - Dual-ascent entropy weight toward a floor on the draft head (#109: weight 36, entropy 0; oscillates at faster rates)
  - --draft-h-in-floor 2 or 3 as a lab meta card judged by the main-pilot answer key and the one-type pilot gate (013-meta-hin2/hin3, #115)
  - Floor 3 + ungated --select --candidates 3 from 460 or 479 expecting it alone to stop relapse (scr-resetcap, scr-ctl479, #134, #140)
  - Entropy bonus 0.05 on a reset head on top of the floor (scr-resetent, #134-#137)
- **Untested variants:**
  - Rerun the killed matched ablation (019-meta-select vs 019-meta-select-floor, or scr-gate479 with/without floor) with 2+ reseeds, judged on 40-iteration top-12 distance, largest type and a human-list head-to-head vs pilot-v2. *Distinct:* The only matched floor ablation never finished; cheap and decisive. *Cost:* low-medium (2-4 screens)
  - Floor on draft-scoring draws only, sparing the pilot's training decks (#115 Next, not built). *Distinct:* Distinct mainly before --select; under --select floored draws enter only if they beat the incumbent, and #137 points the cost at field variety. *Cost:* low
  - Floor on the outgoing (cut) choice. *Distinct:* The #127 ratchet is driven by the cut side too; never floored. *Cost:* low
  - Floor annealed or tied to the head's own entropy. *Distinct:* Changes when the floor acts rather than its level. *Cost:* low
  - Floor on the candidates drawn for --select only, kept apart from REINFORCE's draws. *Distinct:* Separates exploration of candidates from the head's gradient samples. *Cost:* low
- **New hypotheses (section 6):** H73, H93, H94, H110, H111

### H33 · N6 · inconclusive (weak) · A slower draft head collapses less

- **Mechanism:** A smaller REINFORCE step for the draft head slows the softmax's collapse onto one card, though it cannot change the fixed point.
- **Verdict:** --draft-lr 3e-4 is adopted as a neutral default (main_args), but the only direct test (#118) forked at 340 from a head already collapsed to 0.09-0.32 nats and passed by one card of Trainer range inside fork noise. Every fresh head since then collapsed at 3e-4 within 10-30 iterations, with incoming entropy no different from 1e-3. 'Slows collapse from an open head' is untested because there is no matched 1e-3 vs 3e-4 run from a reset head (leaning refuted).
- **Tests:**
  - #118: 015-meta-draftlr3 (340 -> 380, vs 1e-3): Trainer range 4 vs 5; answer key 0.815/0.855 vs 0.805/0.848; pilot gate -6.8 Elo [-18.9, 5.4] (adopted (underpowered: one fork from a collapsed head))
  - #119: Range 8 over 360-399 mixes pre-adoption 1e-3 (360-379); post-adoption 380-399 range 4 (n/a (misattributed window))
  - #126: Post-adoption: median Trainers 24 at 400 -> 15 at 439; best decks 7.9/23.6/28.5 -> 7.8/15.8/36.5 (distance 20.5 -> 36.5) (refuted (collapse continued))
  - #127 vs #109, #92: h_in 0.13-0.27 at 438-447 (3e-4) vs 0.09-0.32 at 296-319 (1e-3) and 0.2-1.1 in #92 (no entropy difference)
  - #131, #132: scr-reset at 3e-4: 5.60 -> 3.35 nats over 460-468, 1.02 -> 0.24 over 478-490; relapsed into Chansey/Snorlax (refuted (no 1e-3 control))
  - #134: scr-resetcap at 3e-4: 3.1 -> 2.6 -> 3.0 -> 1.1 nats; largest type 9 -> 72; distance 7.5 -> 15 (refuted (no 1e-3 control))
  - #133: scr-gamma at 3e-4: incoming entropy 0.49 -> 0.28 over 490-498 (refuted (no 1e-3 control))
  - #121, #123: 017 league fresh head 1 at 3e-4: 5.59 -> 4.65 -> 2.77 nats over 400-419, drafted toward main type (refuted (no 1e-3 control))
  - #124: 016-scratch-recipe-m from 380 at 3e-4: collapsed into no-attack deck-out Pokemon piles (refuted (no 1e-3 control))
- **Do not repeat:**
  - --draft-lr 3e-4 vs 1e-3 forked from an already-collapsed head (any state after about 290) and judged on one fork by the 40-iteration Trainer-range rule (015-meta-draftlr3)
  - Reset head at --draft-lr 3e-4 with selection, 3-nat floor and group changes from 460 (scr-reset / scr-resetcap / scr-gamma)
  - Fresh league heads at --draft-lr 3e-4 from 400 (017-meta-league3-m)
- **Untested variants:**
  - Matched reset-head runs at --draft-lr 1e-3, 3e-4 and 1e-4 from the same state, several seeds, measuring iterations until incoming entropy < 1 nat. *Distinct:* Same mechanism, but the first adequate test of it: 015 started collapsed and all reset screens used 3e-4. *Cost:* medium (about 3 screens x 20 iterations)
  - Draft lr below 3e-4 (e.g. 1e-4) alone. *Distinct:* Step size only; likely slows learning with the same fixed point. *Cost:* low
  - Trust-region or clipped-ratio updates for the draft head (PPO-style clip, or per-update KL cap to the previous head). *Distinct:* Bounds policy movement per update rather than gradient scale; never applied to the draft head (#135's KL anchor is for the pilot). *Cost:* medium (build plus screens)
- **New hypotheses (section 6):** H93, H94, H111

### H34 · N6, N7 · weakened (moderate) · Restart the draft head (draft-reset)

- **Mechanism:** A newly initialised head with selection, the 3-nat floor and group changes explores away from the collapsed head's favourite cards, until its own choice narrows again.
- **Verdict:** Human shape is supported, but only for a while. Against its matched no-reset control (scr-practice, 18.8-23.7 cards off), a reset head reached 10.7-14.8 (scr-reset), and 7.5 with the type cap (scr-resetcap). The shape then relapsed within 10-15 iterations as head entropy fell to 0.24-0.56 nats. 'Other types' failed in all eight --draft-reset screens (seed 1 from seg_0460) and in the fresh league heads, but every one was judged by the walls-biased own pilot (0.72-0.76), so that half is confounded rather than cleanly refuted.
- **Tests:**
  - #130, #131: scr-practice (matched no-reset control, seed 1, same fork): 24.5-29.2 by 478, 18.8-23.7 over 482-488 (control)
  - #130-#132: scr-reset: 36 -> 10.7-14.8 over 478-490, stopped at 491 on plateau; h_in 1.02 -> 0.24; largest type 48 at 483 (log), 61 at 491 (checkpoint, 4 Chansey/4 Snorlax) (mixed (shape held, type relapsed))
  - #131-#133: scr-gamma (+gamma 0.995): 14.5-22.2, then 17.8-21.2 over 490-498; largest type 72 at 499 (checkpoint) (mixed)
  - #132-#137: scr-resetcap (+type cap, turnover every 5): best 7.5 at 487 -> 15.0-20.7 over 494-499; largest type 76 (mixed)
  - #132: Even at peak spread largest types were Chansey/Snorlax (scr-reset 10 at 469 of 80 types; scr-gamma 12 at 479) (refuted (other types))
  - #132, #134: scr-judge2 (reset + pilot-v2 judging 50% share): 23.7-29.3 over 470-478; deck-outs 25% -> 48%; stopped 478 (refuted (did worse))
  - #134, #136, #137: scr-resetent (reset + cap + --draft-ent 0.05): 26.7-32.0 over 465-495; entropy 5.58 -> 4.09; type 23 at 494; Trainers 13-16 (refuted)
  - #135, #136: scr-resetent10 (--draft-ent 0.1) and scr-practice1k: both stopped near 466 for low memory (underpowered)
  - #135, #138: scr-anchor (reset + KL anchor to pilot-v2): 28.7, 24.8, 25.3 over 465-472, matching control; stopped 472 (refuted)
  - #138, #140: From 479 without a further reset: scr-ctl479 relapsed to 13.3-17.3, type 33 -> 74; scr-gate479 held 6-12 cards off (the gate, not the reset, holds shape)
  - #120-#125: Fresh league heads drift to piles (26/16/17, 34/15/11), then learn main type within 10-20 iterations (refuted (other types))
- **Do not repeat:**
  - --draft-reset with --select --candidates 3, 3-nat floor, group 0.3, practice 250, wide turnover, protect 20, seed 1 from seg_0460 (scr-reset)
  - --draft-reset + --gamma 0.995 from 460 (scr-gamma)
  - --draft-reset + --type-cap 0.5 --turnover-every 5 from 460 (scr-resetcap)
  - --draft-reset + --draft-ent 0.05 + type cap from 460 (scr-resetent)
  - --draft-reset + --judge-pilot pilot-v2 --judge-share 0.5 from 460 (scr-judge2)
  - --draft-reset + --anchor pilot-v2 --anchor-w 0.1 from 460 (scr-anchor)
  - Fresh (uniform) league heads or fresh exploiter heads from 400/420 under the shared pilot (017-meta-league3-m, 018-meta-league3-exploit)
- **Untested variants:**
  - Periodic resets, or reset on collapse (e.g. head entropy < 1 nat). *Distinct:* Every screen reset once at 460; only partly distinct, since each reset restarts the base-rate Pokemon drift and cycles through the 2.6-3.0-nat window; read primacy-bias / plasticity reset literature (Nikishin et al. 2022) and AlphaStar's reset schedule first. *Cost:* low (plus reading)
  - Reset under a fairer judge: search-strength judging (#147/#148) or pilot-v2 as the sole judge. *Distinct:* Removes the F2 own-pilot bias that pulls each new head back to the walls; scr-judge2 used only a 50% share. *Cost:* medium
  - Reset from a different state or seed (all eight screens were seed 1 from 460). *Distinct:* Tests whether the relapse is specific to one fork. *Cost:* low
  - Partial resets: last layers only, or shrink-and-perturb instead of full reinitialisation. *Distinct:* Keeps learned card knowledge while restoring plasticity; never tried. *Cost:* low-medium
- **New hypotheses (section 6):** H93, H94, H108, H110, H111

### H35 · N6, N11 · untested (weak) · The draft head reads decks through the pilot

**Evan:** his idea (rule 4: tried first and fully).

- **Mechanism:** Encoding a decklist as a synthetic pre-game state through the pilot's encoder gives the draft head the pilot's learned card knowledge.
- **Verdict:** This is in force as a binding design rule (Evan's rule 3), but no ablation has shown that reading through the pilot gives the drafting any game knowledge. The only probe (#65 cosine: 0.36, 0.64 with an opponent list, 0.72 real vs real) was on pilot-v2's joint encoder. Since 290 (#105), H_j and E_c have come silently from a 1-layer deck encoder (dx) that has never been probed. The indirect evidence runs against the effect, though head collapse (F3) confounds it: drafting dropped Oak and Bill, which the pilot values above Energy (#92, #109), and no-deck pilots were no worse (#73/#74).
- **Tests:**
  - #65: Same-card token cosine synthetic vs real openings 0.36 (0.27 other card); 0.64 with opponent list; 0.72 real vs real (mixed (representation only; never tested on drafting))
  - #105, #109: deck_mode cross at 290 swapped head inputs to dx without reset; median 10/29/20 at 300 -> 33/8/20 at 313; h_in 0.09-0.32 (confounded natural experiment (read only as head collapse))
  - #92, #109: Archived list 0.666 vs copy with draw group swapped for Energy; yet Bill in 87% of decks at 200, 3% at 219 (against (drafting ignores pilot's values; F3 confound))
  - #73, #74: Pilots with decklist tokens hidden were no worse on held-out decks (against premise (deck tokens may carry little knowledge))
  - #130-#132: scr-v2: drafting through frozen pilot-v2 from wide decks, median Pokemon 15 -> 23 in 4 iterations (against)
  - #130, #131: scr-reset: fresh head on the same reading moved best-deck distance 31.2 -> 19.3, fastest (suggests the head, not the reading, binds)
  - #43, #46: Pilot-embedding novelty bonus: modest gain, not reliably replicated (weak related evidence)
- **Do not repeat:**
  - Re-measuring the synthetic-vs-real cosine on pilot-v2 or another joint-mode pilot (#65); the main line reads through dx since 290
  - Carrying a draft head across a change of pilot architecture or reading path without --draft-reset (as at 290, #105 -> #109)
  - Building 'read the deck-free deck encoder directly' (#72 Next) as a new variant: H_j and E_c already come from dx since #105
- **Untested variants:**
  - Reading ablation: head on learned per-card embeddings (or pilot card_emb rows with no encoder) or a frozen random encoder vs the pilot reading, same fork with --draft-reset. *Distinct:* The only direct test of the mechanism. *Cost:* low
  - Re-run the #65 cosine probe on the current cross-mode pilot (dx at deck tokens), with and without opponent lists. *Distinct:* The current reading path has never been probed. *Cost:* low
  - Read candidate cards from real opening states from recorded games instead of the synthetic blank-board state. *Distinct:* Removes the off-distribution input #65 identified. *Cost:* medium
  - Read dx without opponent-list tokens mixed into the same deck self-attention. *Distinct:* Isolates the deck's own representation. *Cost:* low
  - Take h0 from the deck stream's deck_null token instead of the board encoder and fuse. *Distinct:* h0 is the only input still passing through the board encoder. *Cost:* low
  - Deeper deck encoder (deck_layers > 1). *Distinct:* The main line has only ever used a 1-layer deck encoder grown from random init at 290. *Cost:* medium
- **New hypotheses (section 6):** H94

## N7 · Population ecosystem

### H36 · N7 · inconclusive (weak) · Deck-owning agents with separate pilots

**Evan:** his idea (rule 4: tried first and fully).

- **Mechanism:** When each agent owns and pilots its own lineage, no single shared pilot can co-adapt to one deck type, so several types can persist.
- **Verdict:** No deck-owning setup reached the human shape or archetypes: league-3 (Trainers 0-7, Energy 29-36), tournaments N=3/6/9 (0 of 8 archetypes; 29.0/5.3/24.1+1.5) and meta-dev-c (scores 0.00-0.23). Each, however, paired separate pilots with a Pokemon-biased swap operator or with freezing learned heads and no selection. Each was also cut short or hit lab faults, and each kept types apart by construction. Separate vs shared pilots under a fixed operator was never compared, and later evidence (#127, #137) implicates shared-pilot co-adaptation, so the mechanism is untested rather than refuted.
- **Tests:**
  - #54: Both-sides recording: leader 20-23k vs 2-5k transitions; focal-only 2.9-6.5k each; on SharedPilots league-1, stopped in round 0 (n/a (design fix))
  - #55: league-2 (separate networks): stopped round 1; 10 of 10 finalists adopted on 16 games (about +/-12 points) (underpowered (lab fault))
  - #56: Stage-1 and re-test estimates of the same deck differed by up to 25 points (n/a (adoption noise))
  - #57, #58, #59: league-3: types kept (20-card min distance); Trainers 0-7, basic Energy 29-36 by round 6; Tentacool cycle rounds 8-13; stopped round 15 of 30 (refuted as tested (confounded, cut short))
  - #59-#62: Tournament review: anti-imitation weights (60x), unequal budgets, Pokemon-specific generator fixed; tourn-3-loopbug discarded (lab faults)
  - #63: Tournaments N=3/6/9: 0 of 8 archetypes (best 0.43); 29.0/5.3/24.1+1.5; 20% vs archived lists under pilot-v2 (best 41.5%); operator 225/277 Pokemon (refuted as tested (operator confound))
  - #65-#67: meta-dev / meta-dev-c (N=3, own pilots + own REINFORCE heads): a0 9/21/30 -> 50/4/6 -> 3/53/4; 2 of 3 heads froze (3 -> 0.01); 0.00-0.23; stopped 84/150 (refuted as tested (underpowered, no selection))
  - #69: One-pilot 99-deck population: best 0.635 vs tournaments 0.415; its Trainers also fell 22 -> 5 (Trainer shedding not specific to separate pilots)
  - #127, #137: Shared pilot rates walls 0.72-0.76; pilot-v2 0.23-0.24; varied field keeps pilot general (indirect support for the mechanism)
- **Do not repeat:**
  - rl/league.py value-climbing league (deleted in #65): specialists climb their own decks by own value with >= 20 cards from every other agent's deck
  - rl/tournament.py at N=3/6/9 with the uniform-over-card-id swap operator and a fixed per-agent budget
  - SharedPilots league (league-1): one network, agents differing only by a 256-number embedding and a value head
  - Recording both seats in a league with a shared opponent pool
  - Single-stage best-of-finalists adoption on 16 games against one opponent (league-2)
  - meta-dev / meta-dev-c: N=3 per-agent pilots and per-agent REINFORCE heads with a learned change rate, deck moving to every draw, with or without --draft-margin 0.5
- **Untested variants:**
  - Per-niche pilots under the current drafting stack (fixed swaps, --select/--select-z, 3-nat floor, group changes, deck-free encoder) over 99 decks split into niches, with a common or cross-niche judge. *Distinct:* Isolates separate vs shared pilots from the operator confound; #65-#67 used freezing heads with no selection. *Cost:* high (about 3.5 GB GPU per pilot; at most 3 screens)
  - #57's Trainer ablations of each specialist on its own deck. *Distinct:* Shows whether data-thin separate pilots undervalue Trainers. *Cost:* low
  - #63's extra seeds at N=6 and 9 with budget scaled by N-1. *Distinct:* Separates N and seed effects from the mechanism. *Cost:* medium
  - Shared trunk (deck-free board encoder) with per-niche policy/value heads or per-niche LoRA adapters. *Distinct:* Between SharedPilots and fully separate networks; addresses #57's data-thinness while breaking co-adaptation. *Cost:* medium-high

### H37 · N7 · weakened (moderate) · Several draft heads sharing one pilot

**Evan:** his idea (rule 4: tried first and fully).

- **Mechanism:** Several draft heads, each owning a share of the decks, would each find a distinct deck type.
- **Verdict:** Five league runs on the shared, walls-specialised population pilot agree that the heads converge on the walls or lose: 017 fresh, 017 copy, 018 fresh exploiters, 018 copy exploiters and scr-league479 (75 vs 79 Chansey+Snorlax decks against its control). That retires 'more heads on the shared pilot' as a lever. But the 017 fresh card died undecided in a shutdown at 453 (per-head data only to 429), so Evan's approved idea never reached its own decision rule. Separately owned drafting is not refuted: separate-pilot leagues (#57, #63) kept N distinct types.
- **Tests:**
  - #121, #123, #125, #128: 017-meta-league3-m fresh: piles at 409 (26/16/17, 34/15/11); head 1 main type by 419-420; head 2 8/24/27 at 429; died at 453 in shutdown, ~29 of 80 iterations observed (refuted as tested (undecided, lab fault))
  - #121: 017-meta-league3: CUDA out-of-memory at 405, restarted as -m at micro-batch 256 (lab fault)
  - #123, #125, #127: 017 copies (control): three heads 8/23/28-29, h_in 0.05-0.06, vs0 0.47-0.50 at 429; 1 type at 420 (12 best split 6/2/4); stopped by hand 450 (control (drafted alike))
  - #123, #125, #127: 018-meta-league3-exploit fresh: 0.02-0.05 vs head 0; h_in 5.41-5.58; piles 29/17/13, 37/11/12; head 0 to 8/14/38; stopped 450 (refuted as tested (shared pilot))
  - #125, #127: 018-meta-league3-exploit-copy: queued 440, stopped 450, no readings (underpowered)
  - #143, #146, #147: scr-league479 (2 heads, copy, exploit, 479-499): distance 14.0 vs 15.7; C+S 75 vs 79; exploiter 0.508/0.452/0.541; its pilot rates walls 0.718 (refuted as tested (shared pilot))
  - #55-#57, #59-#63: Separate-pilot leagues/tournaments: types = N in all 84 run-rounds, closest pair >= 34 cards; but 29.0/5.3/24.1+1.5 (contrast (per-agent pilots keep types, not shape))
  - #127: Probe variants (Hitmonchan, Chansey/Electabuzz) beat main decks 0.72-0.97 under pilot-v2; shared pilot named as cause (F2 confound documented)
- **Do not repeat:**
  - --draft-heads 3 --draft-heads-init fresh from the main line at 400 under the shared pilot (017-meta-league3-m)
  - --draft-heads 3 --draft-heads-init copy from 400 (017-meta-league3-copy)
  - --draft-heads 3 --draft-heads-init fresh --draft-exploit from the main line at 420 (018-meta-league3-exploit)
  - --draft-heads 3 --draft-heads-init copy --draft-exploit from 440 (018-meta-league3-exploit-copy)
  - --draft-heads 2 --draft-heads-init copy --draft-exploit --candidates 3 --practice-games 250 from the scr-resetcap 479 snapshot, --reseed 2 (scr-league479)
  - Fresh uniform-incoming draft heads on the full 277-card pool with no balancing (017, 018, #124)
- **Untested variants:**
  - One niche-conditioned head under local competition (CVT niches, PATA-EC or play-statistic descriptors). *Distinct:* Conditioning plus within-niche selection rather than separate heads competing globally; descriptors must be game-agnostic (no Energy/Trainer-fraction axes); still inherits F2 without a judge fix. *Cost:* high
  - Draft heads that each own a pilot inside the current learned-head loop. *Distinct:* Tests the shared-pilot confound head-on; only the older swap-operator leagues did this. *Cost:* high
  - The 3-head league judged by search on both seats with a 50-60 turn draw limit. *Distinct:* The only judging setting that ranks the walls below the human lists (0.44-0.46, #147); never used with a league. *Cost:* medium
  - AlphaStar exploiter rules (freeze at 70%, reset, older-snapshot curriculum) on the draft heads. *Distinct:* A schedule, not just a reward; 018 and scr-league479 had none (see H38). *Cost:* medium
  - A head warm-started away from the main type, or with a pool-balanced prior. *Distinct:* Fresh heads never got a fair start: uniform draws are 81% Pokemon. *Cost:* low-medium
- **New hypotheses (section 6):** H111, H112

### H38 · N7 · inconclusive (weak) · Exploiter draft heads find counters

- **Mechanism:** Heads rewarded only against the main head's decks must find decks that counter it.
- **Verdict:** Exploiter draft heads that shared the population pilot failed to escape the walls. 018's fresh heads started at 0.35-0.36 and fell to 0.02-0.05 as their decks drifted to piles; scr-league479's copy exploiter scored 0.45-0.54 and drafted the same walls (75 vs 79 Chansey+Snorlax decks). That pilot, however, rates the walls 0.718 and cannot play counters that beat them under pilot-v2 (0.72-0.97, #127). With their own networks and freeze/reset rules (rl/league.py, #55, #57), exploiters did find counters and new types, though as Energy-heavy piles, so 'exploiters find counters' is not refuted.
- **Tests:**
  - #123-#127: 018 fresh: 0.35-0.36 at 420 -> 0.05/0.02 at 429; h_in 5.41-5.58; piles 29/17/13, 37/11/12; head 0 8/20/31 -> 8/14/38; stopped 450 of 500 (refuted as tested (fresh-head drift, shared pilot))
  - #125, #127: 018 copy: queued for 440, stopped by hand 450, nothing logged (underpowered)
  - #143, #146: scr-league479 (2 heads, --reseed 2, 479-499): 0.595 smoke, 0.508/0.452/0.541 at 480/489/499; C+S 75 vs 79; distance 14.0 vs 15.7; median 13/20/27 (refuted as tested (shared pilot, copy init))
  - #125: 017 all-copies non-exploit control: 0.47-0.48 vs head 0, same as copy exploiter (control)
  - #55: league-1 round 0, own networks: exploiters 0.00/0.06 -> 0.94/0.81 vs leading main deck (supported)
  - #57, #59: league-3 round 7: exploiter e0.0.v4 held 0.43 of equilibrium; 3 types 26-59 cards apart; all piles (29-36 Energy, 0-7 Trainers); stopped round 15 (supported (counters), refuted (shape))
  - #58: league-3 exploiter e1.1 learned a confirm-prompt no-op cycle while losing (lab fault)
  - #127: Hitmonchan variant 0.19-0.39 vs main decks under main pilot, 0.72-0.91 under pilot-v2; probe-chan-buzz 0.94-0.97 (counters exist; shared pilot blocks them)
  - #147: scr-league479's pilot rates walls 0.718 vs human lists (judge not moved)
  - #141, #142: Challengers: wide 0.0 vs best walls; population challengers 0.36 (fresh entrants get little signal)
- **Do not repeat:**
  - --draft-heads 3 --draft-heads-init fresh --draft-exploit with the result-only draft reward under the shared pilot from 420 (018-meta-league3-exploit)
  - --draft-heads 3 --draft-heads-init copy --draft-exploit from 440 under the shared pilot (018-meta-league3-exploit-copy)
  - --draft-heads 2 --draft-heads-init copy --draft-exploit --candidates 3 --practice-games 250 from the scr-resetcap 479 snapshot under the shared pilot (scr-league479)
- **Untested variants:**
  - Exploiter draft head with its own pilot network, or judged by pilot-v2 or by search. *Distinct:* Removes the shared-pilot confound; #55/#57 suggest this is the version that works. *Cost:* medium-high
  - AlphaStar rules (freeze at 70%, reset, older-snapshot curriculum, PFSP-hard) on rl/metagame.py's REINFORCE draft heads. *Distinct:* Run only in rl/league.py with separate pilots; freeze/reset alone never fire at 0.02-0.05 or 0.5, so only the older-snapshot curriculum addresses the observed failure. *Cost:* medium
  - Dense exploiter score from per-step value; cheapest first form --draft-margin on exploiters only. *Distinct:* Gives gradient when every game is lost; caveats: --draft-margin 0.5 sped head freezes (#66-#67), pilot value was exploited (#34, #43, #46), shared value inherits F2. *Cost:* low (margin) to medium (per-step value)
  - Exploiter heads' draws used as challengers (#141 proposal). *Distinct:* Counter-finding through the challenger path; never done. *Cost:* low
- **New hypotheses (section 6):** H87, H111, H112

### H39 · N7 · refuted (strong) · A cap on any type's share keeps diversity

- **Mechanism:** Replacing an overfull type's worst decks with decks from other types keeps several types alive, though the built code only reorders which decks the normal turnover replaces.
- **Verdict:** The cap as built (--type-cap 0.5 with --turnover-every 5, soft and rate-limited to 15 replacements per turnover, 75% wide random decks, young decks protected, Pokemon-overlap descriptor) does not hold the type. It was overrun whenever it bound: scr-typecap 94, scr-resetcap 72-76, scr-ctl479 74, scr-vs479 60-72. A hard, selection-time cap on a descriptor that sees the Chansey/Snorlax walls is untested, and the cap was never separated from the faster turnover.
- **Tests:**
  - #129: Smoke (turnover every iteration, runs/smoke/typecap): largest type 87 -> 73 after one turnover (supported (smoke only))
  - #129, #130: scr-typecap, old head (h_in 0.05-0.2), 460-469: '94 + five of one' before turnovers at 464 and 469; new decks joined main type within 5 iterations (refuted)
  - #132-#137: scr-resetcap: largest type 24, 9, 9, 18, 19, 44 (464-489, below 49.5); cap bound at 494 (72) and 499 (76) and was overrun (refuted)
  - #137: scr-resetent (cap + --draft-ent 0.05): 31, 6, 1, 2, 3, 12, 23 over 464-494; cap never bound; small types from head entropy (n/a (diversity follows the head))
  - #138, #140: scr-gate479 vs scr-ctl479 (both capped): largest 15, 12, 26, 23 vs 33, 48, 74, 74; Chansey+Snorlax 73/99 vs 79/99 (refuted (control overran; descriptor blind to walls))
  - #142, #143: scr-turns70 / scr-turns120 (capped): largest type 42 and 51 at 494; control 74 (refuted)
  - #145: scr-vs479 (capped): largest type 11, 60, 72 at 484/489/494 (refuted)
  - #146, #147: scr-league479, scr-gatevs479, scr-lamv479 (capped): Chansey+Snorlax 75 and 70 of 99 at 499; scr-lamv479 stopped at 495 relapsing (refuted)
  - #53, #57, #121-#125: coevo-1 one type; separate-network league kept 3 types; shared-pilot draft-head league drifted to main type (contrast (only per-agent networks kept types))
- **Do not repeat:**
  - --type-cap 0.5 --turnover-every 5 --turnover-wide --protect 20 with the old (non-reset) head from 460 (scr-typecap, #129-#130)
  - --draft-reset plus --type-cap 0.5 --turnover-every 5 --turnover-wide --protect 20 --select --candidates 3 from 460 (scr-resetcap, #132-#137)
  - The scr-ctl479 recipe (capped, from the resetcap 479 snapshot, --reseed 2) (#140, #143)
  - The soft cap stacked under turn limits 70/120, --vs, league, gate-vs and lam-value screens from 479 (scr-turns70/120, scr-vs479, scr-league479, scr-gatevs479, scr-lamv479)
  - Using the Pokemon-overlap descriptor (deck_kinds) as the measure of diversity for a cap (#140)
- **Untested variants:**
  - Hard, selection-time cap: refuse a --select move or replacement that puts a deck into an overfull type, lift protection for overfull types, MUTANT_SHARE 1. *Distinct:* Tests the family's own mechanism, which the soft rate-limited implementation never did. *Cost:* low
  - Cap on a card-level or embedding descriptor (Chansey+Snorlax co-occurrence, or k-means on the pilot's deck embeddings). *Distinct:* deck_kinds misses the wall archetype (73/99 walls with largest type 15-26). *Cost:* low
  - Cap ablated apart from --turnover-every 5. *Distinct:* No screen separates the cap from the faster turnover credited in #137. *Cost:* low (2 screens)
  - Rectified-Nash niches or payoff-row DPP. *Distinct:* Niches defined by payoff rows, not Pokemon overlap; needs a less biased judge (search plus draw limit, #147), since earlier PSRO with Nash collapsed to one deck. *Cost:* medium
  - MAP-Elites over play statistics (game length, deck-out share, wall presence). *Distinct:* Per-cell local competition removes the 15-per-turnover rate limit; needs per-cell head conditioning or the head redrafts every cell (#130). *Cost:* medium
  - Niche-conditioned draft head or one head per type. *Distinct:* Stops the shared head redrafting capped-out types; overlaps H37. *Cost:* high
  - Fitness sharing (score divided by type size). *Distinct:* Rejected on paper in #129 (singleton fresh decks would take places), never run. *Cost:* low
- **New hypotheses (section 6):** H96, H107, H112, H113

### H40 · N7 · inconclusive (weak) · Turnover feeds new material

- **Mechanism:** Replacing the worst decks with new random or mutant decks keeps the population improving and varied.
- **Verdict:** Turnover was never isolated. meta-99 (#69) is an uncontrolled whole-loop run: Trainers fell 22 to 5, while its best deck against the archived lists rose 0.469 to 0.635. Turnover 0.3 (#97) was judged on the familiarity-biased answer key (+0.012 against a 0.03 rule). scr-typecap's absorption (#130) happened under a head collapsed to 0.05-0.2 nats over 9 iterations. With a reset head, type-capped turnover every 5 kept the field split and the pilot general until the head narrowed (scr-resetcap), so turnover looks like a weak lever that the head and selection override, not a refuted one.
- **Tests:**
  - #67, #69: meta-99 (worst 15% every 10; 3/4 random, 1/4 mutants): medians 19/22/17 at 40 -> 20/5/34 at 120; best vs archived under pilot-v2 0.469/0.565/0.635 (mixed (uncontrolled))
  - #91, #97: 008-meta-turnover30-b (20 iterations): answer key 0.792 vs 0.780 (+0.012, rule 0.03, A/A RMS 0.005); pilot -1.6 Elo [-11.9, 8.7] (inconclusive (familiarity-biased key, off-target))
  - #130: scr-typecap (old head, wide turnover, protect 20, cap): '94 + five of one' before turnovers; replaced decks had scored 0.43-0.58; 9 iterations (refuted as tested (head confound))
  - #130: scr-draft (drops practice, wide turnover, protection together): 31.0 -> 26.0-29.0 vs scr-practice 33.2 -> 28.3 over 460-465 (inconclusive (joint ablation))
  - #131: scr-v2 (frozen pilot-v2, wide decks, wide turnover + protection): median Pokemon 15 -> 23 in 4 iterations (refuted as tested)
  - #120-#125: Per-head turnover in the league of draft heads (5 decks per head per turnover): heads drifted to main type or piles (refuted as tested (shared pilot))
  - #132, #134, #137: scr-resetcap: largest type at turnovers 24, 9, 9, 18, 19, 44, 72, 76; best 7.5-10 while split; pilot-v2 -22.7 Elo vs +27 to +45 on one-type fields (partly supports 'varied' (unmatched))
  - #140: Same cap, gate vs control: largest type 15, 12, 26, 23 vs 33, 48, 74, 74 (selection, not turnover, sets diversity)
  - #141: Wide random challengers score 0.0 against the best walls (against entrants winning places on merit)
- **Do not repeat:**
  - --turnover 0.3 as a lab card judged by the main-pilot answer key (008-meta-turnover30-b, #97)
  - --type-cap 0.5 --turnover-wide --protect 20 --turnover-every 5 with the old, non-reset 460 draft head (scr-typecap, #129-#130)
  - --type-cap 0.5 --turnover-every 5 with a reset head and ungated --select --candidates 3 (scr-resetcap / scr-ctl479, #132-#140)
  - --turnover-wide --protect 20 --init-wide under a frozen pilot-v2 (scr-v2, #131)
  - Per-head turnover inside a league of copied or fresh heads (017-meta-league3 and its copy variant, #120-#125)
  - Joint removal of practice games + wide turnover + protection (scr-draft, #130)
- **Untested variants:**
  - Matched turnover ablation from the 479 snapshot against scr-ctl479: turnover off / on / frozen entrants. *Distinct:* No run has isolated turnover; this is the missing in-repo test. *Cost:* medium (3 screens)
  - Protection ablated alone: --protect 0 vs 20 at an otherwise matched recipe. *Distinct:* scr-draft removed protection only jointly. *Cost:* low (2 screens)
  - Protection that freezes an entrant's composition (no draft moves for N iterations) while the pilot trains on it. *Distinct:* --protect only spares a deck from removal while the head rewrites it (#130); closer to Cheney et al.'s protection of new bodies. *Cost:* low-medium
  - Minimal-criterion admission (admit entrants scoring within a band such as 0.2-0.8). *Distinct:* Filters on viability, not type quota; needs a viable non-wall generator since wide decks score 0.0 (#141) and does not stop redrafting. *Cost:* low
  - Age-based removal (DERL: remove the oldest, not the least fit). *Distinct:* A different selection rule for who leaves; never tried. *Cost:* low
  - Entrants drafted by their own fresh head or a niche-conditioned head. *Distinct:* Keeps entrants from being redrafted into the main type; the league heads drafted pre-assigned decks, not turnover entrants. *Cost:* medium
- **New hypotheses (section 6):** H73, H107

### H41 · N7, N13 · weakened (weak) · A novelty bonus escapes the Energy attractor

- **Mechanism:** A bonus for distance in the pilot's embedding was meant to push the deck search toward diverse archetypes, but the same co-adapted pilot defines both the score and the distance.
- **Verdict:** The only tests used kNN pilot-embedding novelty at lambda 0.03 on the retired start-of-game-value search builder: 3 seeds, 8 iterations each. They give Trainer-rich decks in 1 of 3 seeds (s3), and coevo-1 with that builder still collapsed to one type. Nothing shows whether a novelty or diversity term works in the current REINFORCE draft loop, at another lambda, or in an embedding the judge does not control, so the result is underpowered rather than refuted.
- **Tests:**
  - #43: Novelty 0.03, seed 3, 8 it: deck 15/24/21; 70.2% vs 55.3% under the scratch pilot, only 45.7% vs 38.7% under result #1's pilot. (inconclusive)
  - #46: Seeds 3-5: mean +8.1 / +1.5; s4-s5 at 32-36 Energy; at s5 base beat novelty (60.4 vs 53.6); base alone found a 19-Trainer/24-Energy deck. (weakened (judged mostly seed luck))
  - #47: Novelty 0.03 fixed in every arm, so it re-scores #46's runs; staple Trainers 8.0 for s3 and 0-2 for every other run (archived mean 20.0). (not a test of H41; weakens the Trainer prediction)
  - #52/#53: coevo-1 with the novelty-0.03 builder: from round 7 every support deck held Hitmonchan/Scyther/Chansey; 28-31 basic Energy; all 18 exploration decks retired. (weakened)
  - #39: Distance to the population as one input of a learned strength scorer: 18-25 Energy but weak decks (30.7% vs field); confounded by the scorer change. (inconclusive)
- **Do not repeat:**
  - kNN pilot-embedding novelty (k=5, lambda 0.03) on the start-of-game-value search builder with #43's settings (cold:16, 8 it, 48 games per pair, 4 new decks, 120 s), seeds 3-5 (#43, #46); the flag and builder were deleted in the simplify step, so this bans rebuilding that setup, not novelty in general
  - novelty 0.03 combined with --common-deals at seed 3 (#46: 50.6 vs 71.8)
  - novelty 0.03 combined with the edit head in --head-mode screen / combine / agree, or with --edit-head alone (#43, #47)
  - co-evolution of one pilot with the novelty-0.03 value-search builder over the full pool (coevo-1, #52/#53)
- **Untested variants:**
  - Novelty or diversity term in the current REINFORCE draft loop (rl/metagame.py draft reward or selection). *Distinct:* Never ported; no 'novelty' anywhere in rl/. The loop's existing diversity tools (type cap, entropy floor, turnover, group changes) are structural, not reward-based. *Cost:* medium
  - Lambda sweep or adaptive lambda (DvD-style). *Distinct:* Only lambda 0.03 was ever run; proposed in #43 Next and never tried. *Cost:* low once the term is ported
  - Novelty in a judge-independent embedding (card-count vectors, rules-text embeddings, or pilot-v2's frozen encoder). *Distinct:* Removes the F2 confound: the co-adapted pilot no longer defines the diversity measure. *Cost:* low-medium
  - Novelty with local competition (NSLC): each deck competes only with its nearest neighbours. *Distinct:* Local competition replaces a global bonus. Overlaps the review's niche-conditioned head (CVT / PATA-EC); do not double-count it. *Cost:* medium
  - Behaviour-space diversity: DPP over payoff rows or PATA-EC rank descriptors. *Distinct:* Diversity in whom a deck beats rather than in how it looks; listed as untried in #144. It probably belongs in its own family. *Cost:* medium-high
  - Card-overlap novelty filter on proposals (notes/tcg-rl-research-notes.md line 174). *Distinct:* Acts as a proposal filter, not a reward bonus; proposed but never logged as run. *Cost:* low

### H42 · N7, N12 · supported (moderate) · Population shape swings stochastically

- **Mechanism:** A draft head whose incoming choice collapses to one card drives a forced-move ratchet that swings the population's shape, with seed noise on top. It is not mainly noise in selection, since --select did not exist until #127.
- **Verdict:** The swing is well documented: median Trainers ranged 7-22 in every 40-iteration window from 150 to 319, and forks diverge. That it happens 'by chance' is weakly and confoundedly shown: the cited swings came from a forced-swap ratchet driven by the collapsed head, a 3-nat floor removed most of the swing (#115), and relapse reproduces from one state (#138/#140). No matched multi-seed A/A has been run.
- **Tests:**
  - #92: Median Trainers 5 (150), 15 (162-165), 6 (186), 12 (201-204), 2 (216); tracks the head's incoming card kind (basic Energy 0.84, Trainers 0.6-0.8, basic Energy 0.91-0.93). (supported (swing; points to head collapse, not chance))
  - #104: Median shape distance 42.5 at 240 to 12.5 at 285-289; Trainers 7 to 22; steady one-direction move with no credited cause. (consistent)
  - #109: 10/29/20 at 300 to 33/8/20 at 313 after deckcross-w; Snorlax at 0.9999; head entropy 0.09-0.32 nats; Trainer range 7-22 per 40-it window over 150-319. (supported (deterministic ratchet))
  - #112: Two forks at 318: 31/8/20 vs 13/27/19, but the forks differ in lr (1e-4 vs 2e-4). (confounded; not an A/A)
  - #102: A/A forks at 160: best-deck distance +10.5 and +3.5 vs main after one segment (RMS 7.83); n=2, best decks only, 10 it. (supported (weak))
  - #115: 3-nat incoming floor cut the 40-it Trainer range to 3 (main line 8); a 2-nat floor gave 10. (supports head-collapse cause)
  - #127: Head's top card cycles Bill 0.97 ... basic Energy 0.85-0.98; 87-97% of best decks' moves are null Energy-for-Energy swaps. (supports forced-swap ratchet)
  - #132, #134/#135: Reset head reaches 11-14 cards off in 20-30 it in three screens; scr-resetcap distance 7.5 at 487 to 20.7 as head entropy fell 3.0 to 0.56 nats. (reproducible dynamics)
  - #138/#140: scr-ctl479 (--reseed 2) replicated scr-resetcap's relapse: largest type 33/48/74/74 vs 44/72/76; top-12 distance 15.7 vs 17.2. (against pure chance)
- **Do not repeat:**
  - Reading a single fork's population shape over fewer than 40 iterations as evidence for or against a change (#104, #109, #112, #118)
  - Using forks that differ in a setting (e.g. lr 1e-4 vs 2e-4, #112) as a stand-in for an A/A on shape variance
  - Dual-ascent weight on the head's incoming entropy (#109: weight rose to 36, entropy stayed 0)
  - Incoming-entropy floor at 2 nats on all draws (range 10) or at 3 nats on all draws (range 3, pilot -27 to -33 Elo) (#115)
  - Ungated --candidates 3 reseeded fork of the 479 snapshot as a relapse replicate (scr-ctl479, #138/#140)
- **Untested variants:**
  - Matched multi-seed A/A: 3 or more --reseed forks of one state with identical settings (including lr), median shape over 40 iterations, in both forced-move and --select regimes. *Distinct:* It is the only design that separates seed noise from the deterministic head-collapse part of the swing; the log has only the two-branch, one-segment A/A of #86/#102. *Cost:* medium (3+ screens x 40 it)
  - 3-nat floor applied only to the draft head's counted draws, not to the decks the pilot trains on. *Distinct:* Aims to keep #115's steadying without the pilot's Elo cost; named in #115 Next as not built. *Cost:* medium (needs build)
- **New hypotheses (section 6):** H98

## N8 · Coupling and timescales between levels

### H43 · N8 · inconclusive (weak) · Practice before a draw counts (seasons)

**Evan:** his idea (rule 4: tried first and fully).

- **Mechanism:** A draw judged before the shared pilot has practised it is misjudged, so practising first should let drafting value Trainers.
- **Verdict:** The tested form was --season 5 and 10, with a random season-end move, on the pre-290 pilot and before --select existed, one seed each, forked from 240. It did not move deck shape. Its shape losses are confounded with drafting 5-10x less often than a control that was itself moving, and the answer key rose in both forms (+0.023, +0.049). Practice before judging, per candidate or with selection, is not refuted.
- **Tests:**
  - #99/#100: 008a season 5: answer key 0.745 vs 0.723 (+0.023, rule 0.03); pilot -23.0 Elo [-34.6, -11.4]; population median 8 Trainers / 34-36 Energy at 249-259. (weakened (failed pilot gate and margin))
  - #102: 008a distance 32.3 vs main 21.8 (+10.5), equal to the largest one-segment A/A drift (10.5) and under the bar of 16. (within noise)
  - #101/#102/#120: 008b season 10: answer key +0.049; pilot -3.3 Elo [-15.2, 8.6]; distance 35.8 vs 17.8 (+18.0); closed on a shape bar written after the result. (inconclusive (passed its pre-registered rule))
  - #93/#104: About 10 games per candidate per iteration, so about 40 games of practice per season; 008b median 17/7/36 to 17/9/34 while main moved 42.5 to 12.5 over 240-290. (confound: draft rate and dose)
  - #40: PSRO --pilot-iters 5 (practise then judge at the matrix level): proposals 29-32 Energy; equilibrium one 32-Energy deck. (weakened (different meta level))
  - #131: 20 it practising the 24 human lists (30% of games) raised their score only 0.25 to 0.31. (dose evidence: 40-game seasons underpowered)
- **Do not repeat:**
  - --season K (K>1) with the season-end move to a random candidate, on the pre-select loop and pre-deckcross pilot, forked from main line 240, against an every-iteration-drafting control (008a --season 5 --candidates 4; 008b --season 10 --candidates 2)
  - rl/psro.py --pilot-iters 5 value search (runs/iterated_run.sh, seed 3, 16 random decks, 8 iterations) as a practise-then-judge test (#40)
- **Untested variants:**
  - Adapter fine-tune per candidate before judging, ideally with the Enhanced-POET rule (beat the max of the incumbent's last 5 on direct and fine-tuned scores). *Distinct:* Each candidate gets its own adaptation rather than diluted practice in a shared pilot; appears only in literature notes, never in the progress log. *Cost:* medium-high
  - Seasons with --select / --select-z: keep the practised candidate that scored best at season end. *Distinct:* The practised comparison drives selection rather than feeding one REINFORCE step; --season never ran after #101. *Cost:* medium
  - Seasons matched on draft steps (more candidates per season, or a control drafting every K iterations without practice). *Distinct:* Separates practice from drafting less often, the main confound of 008a/008b. *Cost:* medium
  - Mertan-style equal-adaptation counterfactual: fine-tune equal pilot copies on a wall and on a human list, then replay the match. *Distinct:* Tests the premise (judging bias from unequal practice) directly as a diagnostic; not in the log. *Cost:* low
  - Seasons on the current loop (deck-free pilot, entropy floor, group changes, from 460 or 479) with a matched control and a second seed. *Distinct:* The only tests ran in the pre-290 era with a collapsed head; this changes the setting, not the mechanism. *Cost:* medium-high
- **New hypotheses (section 6):** H86, H108

### H44 · N8 · refuted (moderate) · Closed-loop co-adaptation of one pilot and drafted decks rediscovers the meta

- **Mechanism:** A pilot learning on the drafted decks was meant to correct scorer errors and converge on the human meta, but a shared co-adapted pilot rates highly whatever it has learned to play.
- **Verdict:** Refuted as implemented: the greedy PSRO loop, coevo-1, league-3, meta-99 and the main line 150-460 (one seed each, no seed replicates) all ended Energy-heavy with few Trainers, mostly in one type. Direct probes show co-adaptation amplifies the judge's bias rather than correcting it. Not shown: a loop whose pilot is strong enough to correct the scorer, or one trained under the STS round clock, under which the walls lose (0.40-0.49).
- **Tests:**
  - #40: PSRO closed loop, 8 it, 16 decks, deck-out wins 0: 60.7% vs field (71.9% own pilot); proposals 28-32 Energy; equilibrium one 32-Energy deck. (refuted)
  - #41: Same loop with stochastic picking T=0.03: 19-25 Energy, four-archetype equilibrium (0.36/0.35/0.08...), but weaker: 32.9-43.1% vs field; one seed, never replicated. (partly supported (counter-evidence))
  - #52/#53: coevo-1: Computer Search, Scyther, Oak, ER/SER, DCE rediscovered; every support deck Hitmonchan/Scyther/Chansey from round 7; 28-35 basic Energy; stopped at round 23 of 30. (refuted (confounded with value-search operator))
  - #57: league-3 with separate pilots: three types at round 7, but lineages end at 0-7 Trainers / 29-36 Energy. (refuted on shape)
  - #69/#85: meta-99 median 22/5/32 at 149; 2.8-3.2 of 10 staples; SimpleBot on both sides rates best decks 0.467/0.621/0.579 vs human lists. (refuted on shape)
  - DATA (recomputed, h44_types.py): Largest type 87 (160), 88/82 (240), 70 (280), 58 (290), 84-88 over 320-460; a two-type phase 240-290; same lineage as #69. (refuted (ledger's '70-88 everywhere' was wrong))
  - #132/#133/#134: Own pilot rates new decks 0.71-0.80 vs human lists, pilot-v2 0.20-0.32; population pilots rate main decks 0.75-0.83 and play human lists 27-45 Elo worse than pilot-v2. (co-adaptation amplifies bias)
  - #137/#147: Varied-field pilot about 20 Elo above pilot-v2 still rates walls 0.72-0.76; ten population pilots 0.68-0.75; pilot-v2 0.26 (deck-out-0 trained, also biased). (refuted)
  - #139: STS 20-minute rule with search on the human side: walls get 0.40-0.49 of the points; no closed-loop test had a clock. (confound)
- **Do not repeat:**
  - Greedy PSRO closed loop: rl/psro.py --pilot-iters 5, value search, seed 3, 16 random decks, 8 iterations, deck-out wins 0 (#40)
  - coevo-1: rl/coevolve.py, value search with novelty 0.03, 40% support-vs-support PPO matchups, deck-out win 1, full pool, one pilot (#52/#53)
  - meta-99 recipe from pilot-v2: one pilot, REINFORCE draft head, forced 3-swap draw every iteration, no selection, turnover 15% every 10 (#67/#69)
  - Continuing the main line or the 479 state with pilot-side changes only: practice games 250/1000, KL anchor 0.1 to pilot-v2, --lam-value 1, gamma 0.995, challenger practice, plain-draw turn limits 40/70/120 (#131-#147)
  - Frozen pilot-v2 drafting from wide decks, scr-v2 (#131)
  - pilot-v2 as a second judge at share 0.5, scr-judge2 (#132/#134)
- **Untested variants:**
  - Replicates and a longer run of #41's stochastic-picking closed loop. *Distinct:* Tests whether diversity-preserving selection, not co-adaptation, produced #41's human-like shapes; #41 Next asked for 2 more seeds, never run. *Cost:* medium (psro code must be restored from the pre-simplify tag)
  - Closed loop trained under the actual STS round rule (clock; more Prizes wins 2 of 3 points, Prize tie a draw). *Distinct:* Changes the game's payoff, not the pilot; #139 shows it flips the walls' verdict under search, while #140-#143 tried only plain turn-limit draws. Needs Evan's approval as environment fidelity. *Cost:* medium
  - Closed loop with search-strength judging (one-turn search on both seats plus --max-turns 60; #148 build uncommitted). *Distinct:* Removes the greedy shared pilot's bias at the judging step rather than in training. *Cost:* medium-high
  - Fine-tune the pilot on a candidate before judging large edits (Cheney-style protection of new bodies). *Distinct:* Targets the incumbent type's first-mover advantage directly. *Cost:* medium-high
- **New hypotheses (section 6):** H96, H102, H112

## N9 · Initialisation and bootstrap

### H45 · N9 · partly-supported (weak) · Attack bootstrap: the loop attacks only via pilot-v2

- **Mechanism:** Stated: without a pilot that takes prizes, results reward deck-out piles, so only pilot-v2's deck-out-0 bootstrap makes the loop attack. The record instead implicates the untrained draft head's 81%-Pokémon proposal prior.
- **Verdict:** Shown: a pilot trained on fixed, undrafted decks learns to attack whether deck-out wins pay 0 or 1 (#48, #70-#82), and the from-scratch loop with drafting collapses into deck-out Pokémon piles (#124). Contradicted: that attacking comes only via pilot-v2's deck-out-0 reward. A plain-result pilot attacks and beats pilot-v2 (0.616), R=0 vs R=1 changes little (#33), and an attacking frozen pilot-v2 still drifts to Pokémon piles once drafting starts (#131, 4 it). That points to the draft head's 81%-Pokémon incoming draw.
- **Tests:**
  - #42: pilot-scratch (deck-out wins 0 from the start) 78.7% +/- 4.0 vs SimpleBot at it249; deck-outs 19%, prizes 66%. (pilot-v2 lineage; not a from-scratch stall test)
  - #48: pilot-v2 plateau 83.3% vs SimpleBot at it299 and 349; stopped at 371 of 400. (supports narrow claim (fixed-deck training attacks))
  - #70/#71/#73: base, deck-out wins 1, meta-99 population decks: deck-outs 92% to 7% (it24) to 11% (it79); prizes 0 to 56 to 62%. (contradicts 'only via pilot-v2')
  - #74/#82: Plain-result base beats pilot-v2 0.616 (base-s2 0.624), +85 Elo on held-out decks; vs SimpleBot on archived lists 0.418 (pilot-v2 0.817). (contradicts)
  - #33: Deck-out wins 0 vs 1 fine-tune A/B: greedy deck-outs 27% vs 39%; SimpleBot 93.0% vs 95.5%. (weakens (R=0 is not the attack switch))
  - #124: From scratch: 99% deck-outs, median 59/1/0 at it39; untrained head's incoming draw 81% Pokémon, 2% basic Energy. (supports collapse; points to draft prior)
  - #131: scr-v2, frozen attacking pilot-v2 drafting from wide decks: median Pokémon 15 to 18 to 20 to 23 over 4 it; end never logged. (contradicts (underpowered))
  - #132: scr-scratch, gamma 0.995: deck-outs 61 to 85%, median Pokémon 12 to 25 over it0-4; stopped at 5. (consistent; cannot separate pilot from draft prior)
  - #53: coevo-1 from pilot-v2 with the plain result on drafted decks drifted to an Energy-denial stall (deck-outs up to 41%). (contradicts)
  - #106: 010-pilot-shapeon, non-fading prize shaping 0.1 (a prize-margin term at gamma 1): -31.4 Elo [-50.3, -12.6]. (refuted (margin-in-reward on main line))
- **Do not repeat:**
  - Plain-result (deck-out wins 1) PPO pilot from scratch on a fixed population of undrafted meta-99 decks, run only to see whether it learns to attack (#70-#73, #82: base, base-s2)
  - Deck-out wins 0 vs 1 fine-tune A/B of a4-tok as a test of whether R=0 makes a pilot attack (#33)
  - Non-fading prize shaping 0.1 on the main line (010-pilot-shapeon, #106)
  - Frozen pilot-v2 drafting from wide decks with a fresh head (scr-v2, #131); log its fate rather than relaunch
  - From-scratch drafting with only --gamma 0.995 (scr-scratch, #132)
  - The adopted recipe from scratch under the near-uniform incoming draw (016-scratch-recipe-m, #124)
- **Untested variants:**
  - 2x2 from scratch: incoming draw prior uniform vs card-kind-balanced (kind as first pick or pool-rebalanced), crossed with pilot-v2-initialised vs plain-result-base-initialised. *Distinct:* Separates the draft-prior cause from the pilot-bootstrap cause; grep finds no kind-balanced or per-kind draw. *Cost:* medium
  - Staged run: plain-result pilot trained on rl/deckgen wide decks, then drafting from scratch. *Distinct:* The pilot stage alone is done (#70-#82, on population decks). The staged form is close to scr-v2 (#131), which drifted, so only the use of deckgen wide decks is new; expect failure unless the draft side changes. *Cost:* medium
  - Large-weight prize margin in the pilot's reward from scratch. *Distinct:* Fading potential shaping at gamma 1 already telescopes to a margin term, and the non-fading form failed (#106). Only a large weight from scratch is new, and in a no-Energy pile the margin is 0 (#124). *Cost:* low
- **New hypotheses (section 6):** H92, H99, H104, H109, H110

### H46 · N9 · refuted (moderate) · The recipe rediscovers from scratch

- **Mechanism:** The full loop was meant to climb from random decks and a fresh pilot to the human meta, but a non-attacking pilot and the untrained head's 81%-Pokémon proposal prior pull decks into deck-out piles.
- **Verdict:** The adopted recipe, run unchanged from scratch (016-scratch-recipe-m: one seed, 40 of 160 iterations), slid steadily into deck-out Pokémon piles (59/1/0, 99% deck-outs). scr-scratch (5 it, half scale) adds little and scr-v2 is a frozen-pilot test filed here by mistake. Rediscovering from scratch with a pilot warm-up, a prize margin in the pilot's reward, or a kind-balanced proposal prior has never been run, so only the recipe as it stands is refuted.
- **Tests:**
  - #117/#118, #124: 016-scratch-recipe-m: median 22/17/17 (it0), 40/10/8 (8), 54/3/3 (20), 59/1/0 (39); 1,988 of 2,000 deck-outs; stopped at 40/160 for slot reallocation. (refuted (recipe as-is))
  - #119: Iteration 9: median 42/9/8, 97% deck-outs. (consistent)
  - #132: scr-scratch: 50 wide decks, 1,000 games, gamma 0.995: deck-outs 61 to 85%, median Pokémon 12 to 25, distance 13.0 to 26.0 over it0-4; no stop reason. (underpowered)
  - #131: scr-v2 used a frozen pilot-v2, not a fresh pilot: median Pokémon 15 to 23, distance 16.2/12.8/14.0/19.7 over 4 it; no final state logged. (not a test of this family)
  - #70/#71: Fresh pilot, plain result, fixed undrafted decks: deck-outs 92% to 7% by it24 (11% at 79); prizes 0 to 56 to 62%. (positive control for pilot-first remedy)
  - #69: meta-99 from random decks with pilot-v2: best decks drew even with the human field; median Trainers 22 at it40, 5 by 120. (partial rediscovery, bootstrapped pilot)
  - #121/#123/#125: Fresh league/exploiter heads drift to Pokémon piles (29-37 Pokémon by 429). (consistent with proposal-prior drift)
- **Do not repeat:**
  - Adopted recipe from scratch with drafting from iteration 0 and a uniform incoming draw over the full pool, without a pilot warm-up (016-scratch-recipe-m config, any seed)
  - scr-scratch config: random pilot, deck_mode cross, 50 wide decks, 1,000 games, screens' flags, --gamma 0.995
  - Frozen pilot-v2 drafting a new population of wide decks (scr-v2: --init-from pilot-v2 --freeze-pilot --init-wide) with a fresh REINFORCE head
  - Fresh draft heads (league or exploiters) with uniform incoming choice rewarded only against a strong head 0 (#125)
- **Untested variants:**
  - Remedy (a) from #124: fresh pilot self-plays on random undrafted decks (plain result, deck-out wins 1) until deck-outs fall and prize wins rise, then drafting starts. *Distinct:* Breaks the co-adaptation in which a non-attacking pilot rewards deck-out piles; #71 shows the pilot stage works on fixed decks. *Cost:* medium
  - Remedy (b) from #124: prize margin (the game's end score) in the pilot's reward, as in the draft reward. *Distinct:* Gives a reason to take prizes when nothing can be shaped. Caveat from H45: the margin is 0 in a no-Energy pile, and non-fading shaping cost -31.4 Elo on the main line (#106). *Cost:* low
  - Kind-balanced or exposure-balanced incoming proposal for an untrained head (e.g. kind first, like coevolve's deckgen 'flat' Dirichlet split). *Distinct:* Targets the 81%-Pokémon proposal prior (#124, #121, #125), not the pilot; untested in the metagame loop. *Cost:* low-medium
  - 016 run to 160 iterations or with a second seed, only after (a) and/or (b). *Distinct:* A replicate of a fixed recipe, not a new mechanism; running the unchanged recipe longer is not worth it given the steady collapse. *Cost:* high
- **New hypotheses (section 6):** H99, H100, H103, H104, H110

## N10 · Value and credit learning

### H08 · N10 · refuted (moderate) · Credit does not reach early or Trainer decisions

**Evan:** his idea (rule 4: tried first and fully).

- **Mechanism:** The training signal fades, through delay or per-game noise, before it reaches early, setup or Trainer decisions.
- **Verdict:** Refuted for the expected signal at main-phase decisions with no prompt open, for A4-era pilots (base it79, meta-99 final, pilot-v2 it349) in games of about 126 decisions: at lambda 0.95, credit share is 0.56-0.75 with alignment 0.83-0.95, and Trainer decisions get more one-step credit than average. Not tested: walls-era pilots, the walls' 61-66-turn deck-out games, or prompt and setup decisions; the per-game noise form (SNR 0.14-0.29, and sampled follow-through erasing the value of Trainers) remains open.
- **Tests:**
  - #75: base it79 + meta-99: lambda .95 share 0.56-0.75, alignment 0.83-0.95; value EV 0.88->0.15 at 80+; SNR 0.14-0.29 (lambda 1: 0.03-0.05) (refuted (delay); noise open)
  - #77: New games: share lambda 0 0.288 vs 0.257, lambda .95 0.725 vs 0.647, alignment 0.91 vs 0.89; per-turn bins move up to 0.23 (replicates refutation (overall only))
  - #79: Lambda 0 Trainer share 0.41-0.54 (human lists) vs 0.26 (training decks); lambda .95 0.76/0.78; track often ~0, max 0.66 (refuted (delay); panels confounded)
  - #80: base it79 timing gain +1.32 greedy vs +0.35 sampled follow-through (supports noise form)
  - #73: gae1 (--lam 1): -308.7 Elo, 60.5% of games by deck-out (failed)
  - #77-#78: Value refits on fixed data: whole net overfits from epoch 1; MLP head +0.006 EV; frozen-trunk cross-attention 0.583->0.478 (failed)
  - #89: 003-pilot-vq4-b value cross-attention with trunk: -0.9 Elo [-14.3, 12.5] (failed)
  - #88: 005-pilot-aux (decisions-left and result heads, aux 0.25): -22.6 Elo [-48.9, 3.4] (failed)
  - #105: 010-pilot-lamturn (lambda 1 inside a turn): -37.1 Elo [-56.1, -18.3] after 800 games (failed)
  - #81-#82: base-cont cut timing gain +1.32->+0.39; explore-cont -116 Elo vs base-cont (ordinary training teaches timing)
  - #145-#147: scr-lamv479 (--lam-value 1) stopped at 495 relapsing; as judge rates walls 0.712 (failed)
  - #126-#133: scr-gamma (0.995) moved decks 11-14 cards toward human shape, then relapsed (failed (relapse))
  - #103-#106: Expert iteration on re-dealt one-turn lines: -79/-56/-37 Elo; targets disagreed with pilot 60-70% (failed (noisy per-decision credit))
- **Do not repeat:**
  - qprobe/credit_diag on base it79 and meta-99's final pilot, main-phase no-prompt decisions (#75, #77)
  - qprobe on pilot-v2 it349 and base it79, archived lists, sampled and greedy lines (#79-#80)
  - --lam 1 / gae1 advantages (#73)
  - --lam-turn 1 (010-pilot-lamturn, #105)
  - aux_heads 2 --aux 0.25 on the pooled state (005-pilot-aux, #88)
  - Value refits on fixed data of base it79: whole network, MLP head, frozen-trunk cross-attention (#77-#78)
  - --value-query 4 trained with the trunk (003-pilot-vq4-b, #89)
  - --lam-value 1 in the metagame loop from 479 (scr-lamv479, #145-#147)
  - --explore 0.1 and --ent 0.001 from base it79 (#81-#82)
  - Expert iteration on one-turn re-dealt hard targets, weights 0.3-1.0 (#103-#106)
- **Untested variants:**
  - Credit probe (qprobe/credit_diag) on a walls-era pilot (scr-resetcap 499) over walls-vs-human-list games and the walls' long deck-out games, binned by decisions to the end. *Distinct:* The decisive test in the failure regime, where value EV drops to 0.15. *Cost:* low (~30-40 min a run)
  - Probe prompt and setup decisions (opening placement; choices inside Oak, Computer Search, Item Finder). *Distinct:* qprobe skips any decision with a prompt open, so the 'setup' half is unmeasured. *Cost:* low
  - Variance-reduced advantages with explicitly paired engine RNG (common random numbers, re-dealt paired baselines). *Distinct:* Attacks one-game SNR directly, not value capacity or lambda; #83 showed forks are not CRN, #96-#106 that few lines are too noisy. *Cost:* medium or more
  - Per-card credit inside the draft head's 6-swap REINFORCE draw. *Distinct:* Different level: whether result-only draft reward reaches individual Trainer-vs-Energy swaps. *Cost:* low-medium
  - [outside research] Low-variance advantage estimation for long-horizon imperfect-information games (RUDDER-style redistribution, VINE/paired rollouts, CRN baselines). *Distinct:* Not covered by the first review (GAE, DouZero only); warranted only if the walls-era probe leaves the variance route open. *Cost:* deep research
- **New hypotheses (section 6):** H80, H105

### H47 · N10 · weakened (moderate) · More value fitting or a richer readout

**Evan:** his idea (rule 4: tried first and fully).

- **Mechanism:** The weak value was thought to be under-fitted or to read too little; the evidence instead points to a value limited by the number of games.
- **Verdict:** Fitting the value harder on fixed self-play data (about 5,200 games) is refuted with strong evidence. The pooled MLP gains 0.006 EV, and both the whole network and a frozen-trunk 4-query readout overfit from epoch 1 (#77, #78). A richer readout trained with the trunk rests on one 2-segment lab fork from 180, judged only by Elo against a 20-Elo bar (-0.9 [-14.3, 12.5]), with held-out EV never measured; it is inconclusive, and more data was never tried.
- **Tests:**
  - #77: Fixed 622k decisions (~5,200 games): whole net held-out EV 0.588 to 0.482/0.394/0.387/0.350; value MLP alone 0.600/0.599/0.595/0.589 (+0.006). (refuted (fixed-data refit))
  - #78: value_query 4 readout on frozen trunk: 0.590 to 0.583/0.545/0.517/0.478; no epoch kept. (refuted (frozen trunk))
  - #87: 003-pilot-vq4 forked at 160: -14.3 Elo [-26.1, -2.5] at 170 over 2,000 games; closed as rebased; size of the reseeded A/A branch (-13). (inconclusive)
  - #88: 003-pilot-vq4-b early check at 190: +1.7 Elo [-12.6, 16.1] over 1,200 games. (inconclusive)
  - #89: 003-pilot-vq4-b at 200 (grown at identity from 180, 2 segments): -0.9 Elo [-14.3, 12.5], H0 vs elo1 20 after 1,600 games; EV not measured. (weakly refuted (no gain of 20+ Elo))
  - #79: base-cont, vq4-cont and vq4/vq4-s2 from scratch (80 it, 2 seeds) parked at Evan's request; never run. (not run)
  - #75: Value EV vs result 0.58 overall, 0.88 at 0-4 decisions left, 0.15 at 80+; one-step value carries 14-36% of an option's effect. (motivation (value is the weak link))
- **Do not repeat:**
  - Value MLP refit on the frozen trunk with fixed self-play data (value_refit.py --head-only, about 5k games)
  - Whole-network refit on the result alone with fixed data (base79-full)
  - value_query 4 readout fit on a frozen trunk (value_refit.py --head-only --value-query 4, base79-headx)
  - value_query 4 grown at identity into the main line as a 2-segment lab card with elo1 20 (003-pilot-vq4 / 003-pilot-vq4-b)
- **Untested variants:**
  - Training-only hidden-information critic (opponent's hand, prizes, deck order). *Distinct:* Adds information beyond the opponent decklist the pilot already sees, not capacity; appears only in #144 and the brief; rule-2 compatible. *Cost:* medium
  - value_tower = N (the value's own transformer blocks). *Distinct:* Separates the value from the PPO-shared trunk (capacity plus freedom from policy interference) rather than adding a readout; built and tested in #77, never run. *Cost:* low-medium
  - Readout trained with the trunk from scratch or over a long continuation (vq4 / vq4-s2 at 80 it, vq4-cont at 40), measuring held-out EV and lambda-0 credit share. *Distinct:* Tests the prediction (higher EV) directly instead of by Elo alone; designed in #77, parked in #79. *Cost:* medium-high
  - More data rather than capacity: fit the value on far more than 5,200 games from a fixed policy, or on a larger replay of past collections. *Distinct:* The family's own diagnosed bottleneck (game count); never tested. *Cost:* medium
- **New hypotheses (section 6):** H81

### H48 · N10 · inconclusive (weak) · Auxiliary game-general targets

- **Mechanism:** Extra targets were meant to give the trunk signal the return lacks, but the tested set added only one non-redundant target (decisions left).
- **Verdict:** One 400-game look at one card shows only that aux_heads 2 on the pooled state, with targets [log decisions-left, final result] at --aux 0.25 (two segments from 170, pre-290 pilot), gives no gain of 20 Elo or more. Half the target set duplicates the value at gamma 1, and the Trainer and credit probes it was built for were never run. The recommended targets (per-player final counters, final prize difference, opponent's next action) are untested.
- **Tests:**
  - #84: Build and smoke only: aux_loss 0.719 on the first update, 40 games. (not a test)
  - #88: 005-pilot-aux at 180: +15.6 Elo [-8.1, 39.6]; at 190: -22.6 [-48.9, 3.4], H0 after 400 games; capped games 62-69 per it at 185-189 vs 7-45 main. (inconclusive (no gain of 20+ Elo))
  - #86: A/A cards: sigma 8.8 Elo between unchanged forks; reseeded copy alone read -13.3. (shows #88 is underpowered)
  - #145/#147: Related value-side change --lam-value 1 (scr-lamv479): judge rates walls 0.712 vs population 0.68-0.75. (cross-reference, not a test)
- **Do not repeat:**
  - aux_heads 2 on the pooled state with targets [log decisions-left, unshaped final result] at --aux 0.25, two segments from the 170-era main line, judged by one 400-game H0/H1 look against elo1 20 (005-pilot-aux)
  - Using the trajectory's final result as an auxiliary target (it duplicates the value target at gamma 1)
  - Deciding an aux-head card on Elo against the main line alone; a rerun must also report the #75/#79 credit and Trainer probes, the #147 walls-vs-human-lists judge score and the long-game slice
- **Untested variants:**
  - Per-player deck-left-at-end counters (own and opponent). *Distinct:* Breaks the outcome into parts tied to the walls' deck-out route (#147: 83 of 110 search-condition wins by deck-out); aux_targets in rl/train.py has no such target. *Cost:* low (plumbing exists)
  - Per-seat Prizes left at game end. *Distinct:* Per-player outcome decomposition (KataGo-style); partly overlaps the existing 0.1 prize shaping. *Cost:* low
  - Opponent's next action type (notes/plan-lab.md item 2). *Distinct:* Models the opponent rather than decomposing the outcome; never built. *Cost:* low
  - Final prize difference as a target (analysis-2026-10-06.md). *Distinct:* Carries margin information that the win/loss result lacks. *Cost:* low
  - Aux targets on the post-290 architecture, on a varied field, with a weight sweep (e.g. 0.1 / 0.5 / 1.0). *Distinct:* A change of setting, not mechanism, but needed before closing the family; game-ending turn alone overlaps decisions-left and is not new. *Cost:* medium
- **New hypotheses (section 6):** H81

### H49 · N10 · refuted (strong) · Longer credit for advantages

**Evan:** his idea (rule 4: tried first and fully).

- **Mechanism:** Monte Carlo advantages were meant to learn long-range effects, but the long-range credit already reaches back at lambda 0.95, and lambda 1 mainly adds variance.
- **Verdict:** Full lambda 1 for advantages (with Monte Carlo value targets), from scratch, 40 iterations, seed 1, is strongly refuted (-308.7 Elo, replicated at -310.5). The credit probe (#75) contradicts the mechanism: lambda 0.95 already carries 56-75% of an option's effect, and lambda 1 multiplies the noise. In-turn lambda 1 is only weakly refuted (-37.1 Elo after one segment, competence never read); a warm start and lambda between 0.95 and 1 are untested.
- **Tests:**
  - #73: gae1 --lam 1 from scratch, 40 it, seed 1, lr 3e-4: -308.7 Elo (SE 10); training deck-outs 60.5% vs base 5.2%; prizes 13.7% vs 57.2%. (refuted (from scratch))
  - #74: Second ladder -310.5 +/- 9.1; 0.134 +/- 0.033 vs base; 0.085 / 0.139 vs SimpleBot on archived / held-out decks. (refuted (replicated ladder))
  - #105: 010-pilot-lamturn from 280: -37.1 Elo [-56.1, -18.3] after 800 games; stopped by Elo gate after segment 1; s1 competence never read. (refuted (weak, Elo only))
  - #75: One game's SNR 0.03-0.05 at lambda 1 vs 0.14-0.29 at 0.95; lambda 0.95 credit share 0.56-0.75, alignment 0.83-0.95. (contradicts mechanism)
  - #77: With the refit value, credit share at 0.95 was 0.725 vs 0.647; further value fitting did not help. (value head, not horizon, is the weak link)
- **Do not repeat:**
  - --lam 1 from scratch with Monte Carlo value targets (pilot ablation gae1, 40 iterations, seed 1, lr 3e-4) (#73/#74)
  - --lam-turn 1 forked from the main line at 280 on the joint encoder, one segment, Elo-gated (010-pilot-lamturn, #105)
  - --lam-value 1 in the metagame loop forked from 479 with scr-ctl479's flags (scr-lamv479, stopped at 495) (#145/#147)
- **Untested variants:**
  - Policy lambda between 0.95 and 1 (e.g. 0.97-0.99). *Distinct:* Differs only in degree (bias-variance), proposed in #73 Next and never run; low priority given #75's SNR data. *Cost:* low
  - Lambda 1 for policy advantages with the value kept bootstrapped (lam-value 0.95). *Distinct:* #73 coupled noisy advantages with noisy value targets; this separates them. *Cost:* low-medium
  - Lambda 1 (overall or in-turn) from a warm start on the deck-free main line. *Distinct:* #73 started where 89% of games end by deck-out (#70), so -309 mostly measures slower learning to end games; in-turn lambda 1 never ran on the deck-free line. *Cost:* medium
  - In-turn lambda 1 decided by its intended s1 competence score (Trainer-first, PlusPower puzzles) over both segments. *Distinct:* #105 was stopped on Elo before s1 was read. *Cost:* low-medium
  - Variance reduction paired with lambda 1 (more games per iteration, larger PPO batch, or per-decision baselines from search). *Distinct:* #75 names noise, not horizon, as the failure; this attacks the noise. *Cost:* medium

### H50 · N10 · underpowered (weak) · Monte Carlo value targets

- **Mechanism:** Unbiased Monte Carlo value targets were meant to improve long-game play and so lower the judge's rating of the walls.
- **Verdict:** One fork, scr-lamv479 (--lam-value 1 from the already relapsing 479 snapshot, one seed, 16 iterations, value head still re-fitting), gave a null judge reading (walls 0.712 vs control 0.714) and a slightly faster Trainer decline (17 vs 21 at 495). Competence and the long-game slice were never measured, so the mechanism is untested. What makes the family unpromising is the related advantage-side evidence (#73 -308.7 Elo, #105 -37.1, #75 SNR), not this test.
- **Tests:**
  - #145 (smoke): v_loss 0.572 vs 0.09 on a 160-game smoke run; not comparable, since MC targets carry the whole game's outcome variance. (not evidence)
  - #147 / scr-lamv479 log.jsonl: v_loss 0.48-0.61 vs ctl 0.095-0.12; median Trainers 29/24/19/17 (481-495) vs ctl 29/27/23/21; median 14/17/28 vs 13/21/25 at 495; stopped at 495. (no benefit (slightly faster relapse))
  - #147 (judge): Walls vs human lists under the lamv pilot 0.712 vs scr-ctl479 0.714 (SE about 0.013, 1,152 games); checkpoints 495 vs 499. (null)
  - #73/#74: Advantage-side lambda 1 from scratch: -308.7 / -310.5 Elo; value loss 0.75 vs MC targets. (prior against MC credit)
  - #75: MC (lambda 1) one-game SNR 0.03-0.05 vs 0.14-0.29 at 0.95; value EV 0.88 at 0-4 decisions out, 0.15 at 80+. (prior against MC credit)
- **Do not repeat:**
  - --lam-value 1 forked from scr-resetcap 479 with scr-ctl479's recipe and --reseed 2, without --max-turns or search judging (scr-lamv479, #145/#147)
  - --lam 1.0 for policy advantages from scratch (gae1, #73/#74)
  - Lambda 1 inside a turn (010-pilot-lamturn, #105)
  - Whole-network value refit on fixed self-play data (value_refit.py, #77)
- **Untested variants:**
  - --lam-value 1 for a long run in rl/train.py (or from scratch) with a ladder or SimpleBot competence read. *Distinct:* Measures the stated mechanism (long-game play) directly, which the 16-iteration metagame fork did not; the flag has been in train.py since #77 and never run. *Cost:* medium
  - --lam-value between 0.95 and 1 (e.g. 0.98). *Distinct:* A weaker form of the same mechanism with less target variance; suggested in #73 Next, never run. *Cost:* low
  - --lam-value 1 combined with --max-turns 60 and search-strength judging. *Distinct:* Removes the shared-judge confound (#147: every pilot-side change gives 0.68-0.75). A re-test rather than a new mechanism, worth running only once that regime is adopted. *Cost:* medium-high
  - Auxiliary outcome heads (prizes left, deck left, game-ending turn). *Distinct:* Denser value supervision rather than unbiased targets; see H48. *Cost:* low
  - Oracle or hidden-information critic (PerfectDou-style). *Distinct:* Cuts target variance by giving the critic the hidden zones; see H47. *Cost:* medium
- **New hypotheses (section 6):** H81

### H51 · N10 · partly-supported (moderate) · Self-play learns stall under result-only reward, gamma 1

- **Mechanism:** A deck-out win pays like a prize win, so in slow metas the pilot learns to win by running the opponent's deck out rather than by closing on prizes.
- **Verdict:** Pilots paid 1 for a deck-out win do learn a stall-to-deck-out plan in slow wall or Energy Removal metas and on the archived field, and population judges reward that plan (walls 0.68-0.75 vs pilot-v2 0.264, #147). Not shown: that deck-outs grow in training in general (they fell under the same reward in #57, #71/#73 and #126), that gamma 1 is the cause (gamma 0.995 did not hold deck-outs down, #132-#133), or, either way, that stall explains the Trainer devaluation (#33 underpowered, mixed).
- **Tests:**
  - #32: a4-tok on archived field: 987/2,208 deck-outs (45%) vs SimpleBot 28/200 (14%); a5-cold2 one deck, Computer Search/Item Finder/DCE 0. A level at one checkpoint, not growth. (supported (level only))
  - #33: Greedy deck-outs it24 7%, it74 32%, it149 26%, it249 44% (not monotonic); 15-it control fine-tune sampled deck-outs 61.0% -> 55.6%. (partly-supported)
  - #53: coevo-1 deck-outs 2-8% rounds 0-4, up to 41% at round 13, back to 35% at rounds 22-23 with no change. (partly-supported)
  - #131: 35% deck-outs in a 4,320-game evaluation probe (main decks and variants vs 24 human lists); shows the pilot does not close games, not training growth. (supported (evaluation only))
  - #71, #73: Base from scratch, deck-out win 1, gamma 1: 92% at it0 -> 7% by it24, 11% at 79; last 10 of 40 it 5.2% (base), 12.2% (base-s2); gae1 60.5%. (counter-evidence)
  - #57: league-3 deck-outs 43% at round 0 -> 3-8% from round 2 under the plain result. (counter-evidence)
  - #119, #126: Main line deck-outs 40-61% over 334-399, then 59% -> 13% over 400-439 with no reward change; Computer Search, Bill, Energy Retrieval still left. (counter-evidence)
  - #131-#133: gamma 0.995: scr-gamma 13-19% over 477-484, then 30-44% over 490-498; scr-scratch 61% -> 85% in 5 iterations. (weakens gamma-1 cause)
  - #40, #42, #48: Deck-out wins 0: closed-loop deck-outs 0.40 -> 0.12; human-free pilot 19% vs a4-tok it249 44% on archived field. (supports reward effect)
  - #137: Walls'/human pilot 2x2: 0.720 / 0.761 / 0.237 / 0.233; under own pilot walls won 941 by prizes, 601 by deck-out. (stall is part, not all)
  - #139: One-turn search on human side: 51% deck-outs; 85 of walls' 111 wins by deck-out, median 61 turns vs 34-41 for human prize wins; no-Pokemon win on empty deck mislabelled deck-out. (supported)
  - #141: 109 of 148 walls' deck-out wins already ahead on prizes; nodraw:15 changed 5 of 576 games; walls 0.360 at <=40 turns, 0.784 over 40. (supported (long games))
  - #147: 1,152 games per judge: population pilots rate walls 0.68-0.75, pilot-v2 (deck-out wins 0) 0.264; search both seats + 50-60-turn draw 0.44-0.46; greedy + 60 turns 0.60. (supported, confounded (pilot-v2 also differs in training decks))
  - #69: Forcing Oak and Computer Search first loses 8 points, deck-outs 469 vs 153: in a slow meta stall devalues draw Trainers. (supports Trainer sub-claim)
  - #33: Stall explains Trainer devaluation? 15-it R=0 fine-tune, deck-outs only 39% -> 27%; card values within ±2.0-2.4 at 100 games per deck. (underpowered (not refuted))
- **Do not repeat:**
  - --deckout-win 0 as a training lever (rule-2 shaping, #51); diagnostic only (#33 15-it fine-tune from a4-tok it249; pilot-v2 #48)
  - --gamma 0.995 (pilot GAE only) on scr-reset's recipe from main 460, 40 iterations, seed 1 (scr-gamma, #131-#133)
  - Plain-draw --max-turns 40, 70 or 120 (no prize tiebreak) with greedy judging from 479 (#140, #142, #143)
  - GAE --lam 1.0 from scratch (#73 gae1: 60.5% deck-outs, -309 Elo) and --lam-value 1 from 479 (scr-lamv479, relapsed, #147)
  - nodraw:15 hiding the human side's draw cards on a thin deck (#141: 5 of 576 games changed)
  - Greedy judging with a 60-turn draw limit alone (#147: walls still 0.60)
- **Untested variants:**
  - STS round rule in training: clock, unfinished game to the player with more Prizes at 2/3, Prize tie 1/3. *Distinct:* Pays the prize race at the cut instead of a flat draw; uses only the game's end score (rule 2). Only re-scored offline (#139); #140 built plain draws. Needs Evan's call. *Cost:* medium (engine flag plus one 20-40-iteration screen, ~2-4 h)
  - Prize margin in the pilot's PPO reward (#124 remedy b). *Distinct:* Rewards closing by prizes without labelling deck-outs; margin entered only the draft reward (#66, #90). *Cost:* low-medium (reward change plus one screen)
  - Per-turn or per-decision cost (#32 Next). *Distinct:* A length cost on the objective; close to gamma < 1, so distinct only if the cost is much larger than 0.995's effective discount. *Cost:* low-medium
  - Search-strength judging (--judge-search) with --max-turns 60 (#147, #148). *Distinct:* Attacks stall on the judge side rather than the pilot's reward; under way, not yet measured. *Cost:* medium (running)
  - Re-run #33's card ablation under a pilot never given a stall incentive, or in the population's meta, at enough games per deck. *Distinct:* The only adequately powered test of the Trainer-devaluation sub-claim. *Cost:* medium
- **New hypotheses (section 6):** H102, H103

### H52 · N10 · partly-supported (moderate) · Pay less for deck-out wins

- **Mechanism:** A smaller deck-out reward makes the pilot play for prizes instead of stalling.
- **Verdict:** Paying 0 for deck-out wins does cut deck-outs (#33 27% vs 39%, #40 0.40 -> 0.12, #42 19% vs 44%), but it did not raise Trainer values or move deck shape (#33, #40, #126, scr-v2, scr-judge2, anchor). That pilot-v2's 0.264 wall verdict comes from its deck-out-0 reward is an unisolated attribution, and the lever is banned in training by rule 2 (#51).
- **Tests:**
  - #33: --deckout-win 0, 15 it from a4-tok it249, one seed: deck-outs 27% vs 39%; Bill 49.1/47.6, Oak 67.8/66.0 etc. within ±2.0-2.4; SimpleBot 93.0 vs 95.5. (mixed)
  - #40: Closed PSRO loop fine-tuned at deck-out 0: deck-outs 0.40 -> 0.12-0.22, but proposals ~30 Energy, final deck 32 Energy, no PlusPower, Gust or Computer Search. (refutes Trainer half)
  - #42: From-scratch random-deck pilot at deck-out 0: deck-outs 19% (vs 27% #33 R=0, 44% a4-tok); value stops overrating Energy, but all deck variants 0.61-0.62. (partly-supported)
  - #147: pilot-v2 (deck-out 0, #48) judges walls 0.264 over 1,152 games; walls still win 146 by deck-out vs 104 by prizes under it. (consistent, unisolated (pilot-v2 also differs in decks and league; #139 label bug))
  - #126: Main line deck-outs 59% -> 13% over 400-439 while Trainers fell 24 -> 15 and Energy rose to 36.5. (refutes Trainer half)
  - #131: scr-v2: frozen pilot-v2 drafting from wide decks headed to Pokemon piles; median Pokemon 15 -> 23 in 4 iterations. (negative)
  - #132-#134: scr-judge2 (pilot-v2 as judge, share 0.5): deck-outs 25% -> 48%, distance 23.7-29.3, stopped at 478 as stalled. (negative)
  - #135, #138, #147: scr-anchor KL to pilot-v2: ~65 Elo better on human lists, but its judge still rates walls 0.694. (negative)
  - #70, #71: Matched from-scratch deckout0 ablation arm planned, chain stopped after base/base-s2; never ran. (untested)
- **Do not repeat:**
  - --deckout-win 0 in the training loop (rule-2 shaping, #51); #33 15-it fine-tune from a4-tok it249 already measured
  - --pilot-deckout-win 0 in a closed deck-search/PSRO loop with pilot fine-tuning (#40)
  - Frozen pilot-v2 as second judge: --judge-pilot runs/pilot-v2/model_it00349.pt --judge-share 0.5 (scr-judge2, #132-#134)
  - Frozen pilot-v2 drafting a new population from wide decks (scr-v2, #131)
  - KL anchor to pilot-v2 on practice games to import its wall verdict (scr-anchor, #135/#138; judge 0.694 in #147)
  - Turn-limit draws --max-turns 40/70/120 with greedy judging as a stall penalty (#140-#143)
  - --gamma 0.995 pilot-only on scr-reset's recipe from 460 (scr-gamma, #131-#133)
- **Untested variants:**
  - Matched diagnostic ablation: two from-scratch pilots on wide random decks, deck-out win 0 vs 1, each judging the walls vs the 24 human lists (fix the #139 ending-label bug first). *Distinct:* The only way to isolate the reward from pilot-v2's other differences and confirm or reject #147's causal claim; planned as #70 deckout0, never run. *Cost:* high (two from-scratch pilots, hundreds of iterations)
  - Prize margin in the pilot's reward (#124 remedy b). *Distinct:* Rewards how a win is reached via the game's own end score (rule 2 allowed), not a deck-out discount. *Cost:* low-medium
  - Per-turn or per-decision cost (#32 Next). *Distinct:* General length cost; only weakly distinct from gamma < 1 and turn-limit draws, both tried. *Cost:* low-medium
- **New hypotheses (section 6):** H76, H86, H103, H104

### H53 · N10 · weakened (weak) · Discounting closes games

- **Mechanism:** With gamma < 1 a sooner win is worth more, but as built it discounts the pilot's symmetric +/-1 result only (also softening delayed losses), while draft reward and selection stay undiscounted.
- **Verdict:** A pilot-side symmetric --gamma 0.995 in the PPO GAE, on scr-reset's recipe forked from main 460 (one seed, 460-499), only delayed the rise in deck-outs by about 7 iterations and did not improve shape; the from-scratch scr-scratch arm was stopped at 5 iterations with no control and is inconclusive. Discounting the judge or draft reward, other gamma values and more seeds were never tested.
- **Tests:**
  - #131-#133: scr-gamma vs scr-reset (seed 1, same fork): deck-outs 9-19% vs 11-27% (465-479), 17-18% vs 25-35% (480-484), 30-33% vs 29-31% (490-491), 40-44% at 496-499. Type count not measured. (weakened (lag, not reduction))
  - #132, #133: Shape distance 14.5-22.2 (477-484) and 17.8-21.2 (490-498) vs scr-reset 10.7-14.8 (478-490). (no improvement)
  - #132: scr-scratch gamma 0.995: iterations 0-4 deck-outs 61% -> 85%, Pokemon 12 -> 25, distance 13.0 -> 26.0; stopped at 5, no gamma-1 control. (inconclusive)
  - #71, #73: gae1 (--lam 1.0, gamma 1) 60.5% deck-outs vs base 5.2%: credit horizon moves stall rate. (related)
  - #66, #67: --draft-margin 0.5 (prize margin in draft reward) did not stop freezing; one head froze sooner. (related, negative)
  - #140, #142, #143: Draw turn limits: at 40 most games drawn; at 70 and 120 population relapsed like control. (related, negative)
  - #139, #147: Re-scores: STS round rule walls 0.40-0.49 under human-side search, 0.63-0.68 greedy; draws at 50-60 turns with search both seats 0.44-0.46, greedy T=60 0.60. (related (judge-side))
- **Do not repeat:**
  - --gamma 0.995 (pilot GAE only) on scr-reset's recipe (--draft-reset, no type cap, turnover every 10) from main 460 for 40 iterations, seed 1
  - --max-turns 40 plain draws (most games end drawn, #142)
  - --max-turns 70 / 120 with greedy judging from the 479 snapshot (relapse like control, #143)
- **Untested variants:**
  - Judge-only or draft-reward win discount (payoff falling with game length at deck level), ranked second by the #138 design workflow. *Distinct:* Pays deck-level fitness less for slow wins, where #147 places the bias; never built. *Cost:* low-medium (existing code, one screen ~2-4 h)
  - STS round payoff in training (slow win 2/3, Prize-lead tie 1/3). *Distinct:* Prize-tiebreak clock vs the plain draws tried in #140; needs Evan's call (#139 Next). *Cost:* medium
  - Gamma sweep (0.99, 0.98) or more seeds. *Distinct:* Dose test only (0.995 discounts a game by ~0.34-0.47 over 150-215 decisions); same mechanism. *Cost:* medium (one screen per value)
  - Gamma together with search-strength judging and --max-turns 60. *Distinct:* Pilot-side discount may only matter once the greedy judge is fixed. *Cost:* medium
  - From-scratch gamma 0.995 run of 25-40 iterations with matched gamma=1 control. *Distinct:* Needed to answer #132 Found (3); from-scratch deck-outs need 20+ iterations to fall (#71/#73). *Cost:* medium-high (two runs)
- **New hypotheses (section 6):** H103, H104

### H54 · N10 · weakened (weak) · Lasting prize shaping

- **Mechanism:** Potential-based prize shaping (Phi = 0.1 x prize difference / 6) telescopes to the result at gamma 1, so lasting it only moves credit for prize swings earlier.
- **Verdict:** Switching never-fading --shaping 0.1 onto the warm deck-free pilot at 290 (shaping faded to 0 ~190 iterations earlier) read -31.4 Elo after one 10-iteration segment and was stopped before its competence decision. Not shown: lasting harm versus a value-target transient; and by construction (gamma 1, potential-based) it cannot change the objective or make the pilot close games.
- **Tests:**
  - #106: 010-pilot-shapeon from 290: -31.4 Elo [-50.3, -12.6] after 800 games; stopped at 300 after one segment; competence (s1) never measured. (weakened (one segment, transient confound))
  - #124: From-scratch recipe with shaping 0.1 (0.061 at it39) still collapsed into no-attack deck-outs; shaping inert when nobody takes prizes. (related observation)
  - #70, #71: From-scratch ablation with shaping 0.5 fading was queued; chain stopped after base/base-s2, never ran. (untested)
- **Do not repeat:**
  - Switching lasting --shaping 0.1 onto a warm pilot whose shaping had faded to 0, judged on a single Elo segment (010-pilot-shapeon at 290, #106)
  - Using lasting potential-based shaping at gamma 1 as a way to make the pilot close games or avoid deck-outs (it telescopes to the result)
- **Untested variants:**
  - Lasting shaping judged on the s1 competence score over 2-3 segments after a value-head warm-up. *Distinct:* Separates the switch-on transient from a lasting effect; same credit-timing mechanism. *Cost:* medium (2-3 lab segments)
  - Shaping ramped in gradually, or from scratch at weight 0.5 (planned #70). *Distinct:* Avoids the abrupt value-target shift; still credit timing only. *Cost:* medium-high (from scratch)
  - Shaping combined with gamma < 1. *Distinct:* With gamma < 1 shaping no longer telescopes exactly, adding a small real incentive to take prizes sooner; scr-gamma ran with shaping already faded. *Cost:* medium
  - Prize-margin terminal reward in the pilot (#124 remedy b). *Distinct:* Changes the objective, unlike shaping; belongs to its own family. *Cost:* low-medium
- **New hypotheses (section 6):** H104

## N11 · Pilot architecture

### H55 · N11 · adopted (weak) · Token pointer transformer beats a fixed-id MLP

- **Mechanism:** Card tokens with a pointer over legal options should generalise across decks and cards better than fixed-id inputs.
- **Verdict:** Adopted as an engineering choice: in RL on the A4.1 task the token pilot beat the MLP (93.3% vs 88.5% vs SimpleBot, 65.9-67.8% head to head, 24 of 24 decks), one seed, with A4.1 trained before #20's loop fixes. The stated mechanism, generalisation across decks and cards, was never tested against the MLP, supervised imitation went the other way (69.6% vs 78.3%), and the MiniLM text prior is unablated.
- **Tests:**
  - #25: Distillation: top-1 69.6% vs MLP 78.3% (chance 21.5%); value MSE 0.664 vs 0.866; train loss 0.72 vs 0.06; MLP reads teacher's encoding, 5.2M vs 1.6M params. (mixed/confounded)
  - #26: Field 93.3% ± 1.0 vs 88.5% ± 1.3; mirror 93.2% vs 89.6%; h2h 65.9% ± 1.9 / 67.8% ± 1.9, 24/24 decks; A4.1 trained pre-#20 fixes; one seed. (adopted)
  - #15: ONNX token inference 1.3-5.7 ms per decision vs 0.06 ms MLP (~30x compute). (cost)
  - #42: Token pilot from scratch on 512 random decks: 78.7% ± 4.0 archived (vs a4-tok 92.6%), 67.3% held-out random decks; no MLP arm. (partial (no control))
  - #92: a4-tok it249 Trainer competence 0.41-0.79 by group, no better than population pilots. (no Trainer advantage)
  - #70, #71: --card-inputs feats/ids and small (d192, 3 layers) ablations built, stopped before running. (untested)
- **Do not repeat:**
  - Token vs fixed-id MLP on the 24 archived decks, one seed, A4.1 settings with environments unmatched (#26)
  - Supervised distillation of the A4.1 teacher into a token student vs an MLP student reading the teacher's encoding (#25)
  - Deeper token pilots grown as identity blocks at 6 or 8 layers, lr 2e-4, one segment (#111/#113: -25.2, -19.4 Elo)
  - Slot binding grown onto a trained pilot without warm start (#105/#106: -201 Elo)
- **Untested variants:**
  - Card-input ablation --card-inputs ids or feats (no MiniLM text). *Distinct:* Directly tests the language-prior caveat; code exists (#70). *Cost:* low
  - Fixed-id MLP vs token pilot on held-out decks (#42-style random decks, held-out lineages). *Distinct:* The only test of the stated generalisation mechanism. *Cost:* medium
  - Second seed of #26 with A4.1 retrained on the fixed environment at matched parameters. *Distinct:* Removes the environment and parameter confounds; replication. *Cost:* medium (~3.5 h per run)
  - Wider token pilot (d > 256) by distillation or from scratch. *Distinct:* Capacity by width, distinct from failed depth; warm start cannot change width (#113). *Cost:* medium-high
  - Generic entity tokens instead of Pokemon slots and verbs. *Distinct:* Rule-2 (MTG portability) debt (#51 design notes only); not expected to move the Energy-heavy minimum. *Cost:* high
- **New hypotheses (section 6):** H91

### H56 · N11 · inconclusive (weak) · Capacity limits the pilot

- **Mechanism:** A bigger or deeper pilot should play better, including Trainer sequencing.
- **Verdict:** No clean capacity test exists: pilot-v2's 83% plateau bundled size with count features, a league and deck-out reward and is explained by deck experience (#49); deck-inter mixed +82% parameters with a new architecture; 6/8-layer pilots were stopped after one segment across an lr change, never scored on competence. #25 (token student underfits its teacher) is the only direct evidence and supports a capacity limit.
- **Tests:**
  - #48: pilot-v2 3.24M params (d256/4 layers vs 1.6M) plateau 83.3/83.1/83.3 at 299/324/349 vs SimpleBot; bundled with count features, league, deck-out 0. (inconclusive (confounded))
  - #49: +2 cross-attention blocks fine-tuned 30 it: 88.8/88.7 vs same-architecture 91.0/89.6; experience on decks, not attention, was missing. (inconclusive (archived decks, near ceiling))
  - #72-#74: deck-inter 5,874,178 params (+82%): Elo -15.0 (#73), -12.9 rerun (#74); one seed, 40 it, confounded with architecture. (inconclusive)
  - #111, #113: deep6 +14.3 [-3.7, 32.4] at 320 (lr 1e-4 fork); deep6-b -25.2 [-41.6, -9.0], deep8-m -19.4 [-35.0, -4.0] at 330 (lr 2e-4); one segment, no competence. (inconclusive)
  - #25: Token model 1.6M top-1 69.6%, train loss 0.72 vs MLP 0.06: short of capacity, not overfitting. (supports)
  - #26: 1.6M token model beats 5.2M MLP head to head 65.9%/67.8%: architecture outweighs raw parameter count. (related)
  - #77: Refitting value net on results alone overfits from epoch 1 (~5,200 games vs 3.24M weights): value is data-limited. (against more params without data)
- **Do not repeat:**
  - Deeper pilots grown with identity blocks, forked right after the lr 2e-4 adoption, stopped on one 10-iteration segment's Elo gate (#111, #113)
  - Capacity bundled with count features, league and deck-out reward, judged vs SimpleBot on archived decks (#48, #49)
  - deck-inter (+82% params with new attention), one seed, 40 iterations (#72-#74)
  - deep8 at micro-batch 512 under the 5.30 GB per-process cap (out of memory, #111); use 256
- **Untested variants:**
  - Wider pilot via teacher distillation into a cold wider student, decided on competence and checked against an independent judge (pilot-v2 / SimpleBot panel). *Distinct:* Width route that warm-start growth cannot do (#113); #25 supports underfitting; failed expert-iteration distillations used noisy search targets, not imitation. *Cost:* medium-high
  - Depth run its full 3 segments to a competence decision at a fixed (or lower) lr, with 2+ forks from one state. *Distinct:* Separates the +14/-25 swing from fork noise (#112 forks diverged within 12 iterations). *Cost:* medium-high (6+ segments)
  - Capacity with more data per parameter (more games per iteration or practice games). *Distinct:* #77 shows the value side is data-limited, so capacity alone may not help. *Cost:* medium
- **New hypotheses (section 6):** H91

### H57 · N11 · partly-supported (weak) · Attention variants improve the pilot

**Evan:** his idea (rule 4: tried first and fully).

- **Mechanism:** Missing attention paths or ability information limit the pilot's play.
- **Verdict:** The warm-started deck-free encoder with deck cross-attention gave +36.6, +20.9 and +34.9 Elo and was adopted at 290 (#100, #101, #105), while value cross-attention (#89) and attention memory (#99) were lab negatives and slot binding was neutral (#116); --cand-self, --ability-text and --cross-layers were only underpowered tests (40-it screens, #49 archived fine-tune), so inconclusive. No attention change moved Trainer competence (0.43-0.48 since 160).
- **Tests:**
  - #49: 30-it fine-tune from pilot-v2 it349 on archived decks vs SimpleBot: A 91.0/89.6, B (cross-layers) 88.8/88.7, C (cand-self) 88.2/90.0, D 89.5/91.5, ±0.025-0.039. (inconclusive (near 97.6% ceiling, one run))
  - #73, #74, #75: 40-it screens: cand-self +15.3 Elo (0.525/0.520); ability-text -7.2 (0.514, 0.435 ± 0.049 vs base-s2); SimpleBot 0.269/0.609 and 0.319/0.541; noise ~±15 Elo. (inconclusive)
  - #100, #101, #105: Deck-free encoder warm-started: +36.6, +20.9, +34.9 [15.8, 54.1] Elo; archived gate +5.4 [-11.6, 22.4]; adopted at 290. (supported (strength))
  - #98: Same deck-cross encoder cold (deck-blind): -54.3 Elo at 250; measures the start handicap. (inconclusive)
  - #78, #89: Value cross-attention (value_query 4): held-out EV 0.583 -> 0.478 on frozen trunk; with trunk -0.9 Elo [-14.3, 12.5]. (refuted)
  - #99, #103: Attention memory 009-pilot-memattn -18.3 Elo [-31.0, -5.6], stopped. (refuted (lab))
  - #106, #114, #116: Slot binding cold -201.4 Elo; warm +11.7 then -3.8 [-16.2, 8.5], competence +0.013 vs bar 0.06. (neutral)
  - #111, #113: Depth 6/8 grown as identity: +14.3, then -25.2 and -19.4. (inconclusive)
  - #116: None of 16 pilot cards, deck-free encoder included, moved Trainer competence by its bar. (no competence gain)
- **Do not repeat:**
  - --cand-self and --ability-text as 40-iteration from-scratch screens, one seed (#73, #74)
  - --cross-layers / --cand-self as 30-iteration fine-tunes on archived decks vs SimpleBot (#49; out of scope per #51, near ceiling)
  - Architecture changes that cannot start as identity, cold-started and judged after one segment (deck-cross cold #98, -54 Elo)
  - Slot binding grown cold onto the deck-free pilot (031-pilot-slotbind, #106) or warm-started and decided on competence on the walls main line (031-pilot-slotbind-w, #116)
  - Value cross-attention value_query 4, frozen-trunk refit (#78) or trained with trunk (003-pilot-vq4-b, #89)
  - Attention memory over own decisions (009-pilot-memattn, #99)
  - Depth 6/8 grown as identity at lr 2e-4 decided on one or two segments (#113)
  - deck-inter (+82% params) at 40 iterations (#73)
- **Untested variants:**
  - --cand-self and --ability-text as warm-started lab cards on the deck-free main line, judged on the 2,000-game Elo gate, archived gate and competence. *Distinct:* Never run at lab strength; ability-text targets the 'ability information' half of the mechanism. *Cost:* low-medium (cheap lab cards)
  - Joint state-and-options encoder (#71 Next). *Distinct:* Board would attend to the options, unlike cand-self (options among themselves); never built. *Cost:* medium
  - Decklist dropout in training (#73, #74 Next). *Distinct:* Regularises the deck cross-attention stream rather than adding a path. *Cost:* low
  - Draft head reading the deck encoder directly (#72 Next). *Distinct:* Changes the meta-level representation, not the pilot; may belong to a drafting family. *Cost:* medium
- **New hypotheses (section 6):** H76, H78

### H58 · N11 · inconclusive (weak) · Slot binding

- **Mechanism:** Binding attached cards to their slots (slot embedding plus per-head same-slot attention bias) gives the pilot a truer board.
- **Verdict:** Slot binding was neutral at the budgets tested: one-seed 40-it screens within ±15 Elo noise, a cold graft that measured an input handicap (-201.4), and one warm-started fork over two segments on the walls population (+11.7 then -3.8 Elo, competence +0.013 vs bar 0.06). Its effect on drafted Energy and Trainer counts was never measured, and the base attached-Energy count-feature bug (#71) was never fixed on its own.
- **Tests:**
  - #73, #74: 40-it screen, one seed: vs base 0.505 (#73) / 0.583 (#74), vs base-s2 0.521 / 0.511; Elo +12.6 / +19.5; noise ±15 Elo. (inconclusive)
  - #75: SimpleBot archived/held-out 0.335/0.559 vs base 0.301/0.510 and base-s2 0.344/0.550. (within noise)
  - #72-#75: deck-cross-sb from scratch: Elo -21.5 (#73), -13.2 (#74); vs slot-bind 0.443; SimpleBot 0.320/0.524. (slightly negative, inconclusive)
  - #83, #106: Grown cold at 290: -201.4 Elo [-245.7, -162.4] after 400 games; count features of attached Energy change, so it tests the handicap. (inconclusive)
  - #113, #114, #116: slotbind-w warm start (KL 0.043, agreement 0.898): +11.7 [-8.5, 32.0] at 350; -3.8 [-16.2, 8.5] at 360; competence 0.460 vs 0.447. (neutral (one fork, two segments))
- **Do not repeat:**
  - --slot-bind on the joint encoder from scratch at 40 iterations, one seed, one held-out-deck ladder (#73/#74)
  - deck-cross + slot binding (deck-cross-sb) from scratch at 40 iterations, one seed (#72/#73)
  - Growing slot_bind onto a trained pilot with zero-initialised new weights and no warm start (#83/#106: -201 Elo)
  - Warm-started slot binding (2,000 games, 3 epochs) as a two-segment lab card decided on competence on the walls main line (#113/#114/#116)
- **Untested variants:**
  - Fix the attached-Energy count feature alone (base reads ENERGY aux slot x 8 + copies as a count, so 2 Energy on slot 5 looks like 42; #71 Found 1). *Distinct:* An input-bug fix, not structural binding; bears directly on Energy valuation and the Energy-heavy minimum; never tested. *Cost:* low (feature fix plus warm start and a lab card)
  - Per-Pokemon attached-Energy-by-type features on slot tokens. *Distinct:* Gives Energy type per slot explicitly instead of via the aux id; no attempt found. *Cost:* low-medium
  - Measure slot binding's effect on drafted Energy/Trainer counts and the human-list answer key. *Distinct:* A missing ground-truth readout, not a new mechanism. *Cost:* low
  - Slot binding with several seeds or longer runs (#73/#74 Next). *Distinct:* Power increase only. *Cost:* medium
- **New hypotheses (section 6):** H76, H77

### H59 · N11 · inconclusive (weak) · Memory supplies setup competence

**Evan:** his idea (rule 4: tried first and fully).

- **Mechanism:** Seeing past actions should let the pilot plan setup over turns.
- **Verdict:** On the pre-deck-free pilot (240-280), one seed each over 10-20 iterations: history tokens W=4 gave a null (competence 0.421 vs 0.437, Elo +0.2 [-12.1, 12.4]) and the attention and GRU memories cost strength (-18.3, -21.2 Elo), with their competence never measured. Not shown: that memory cannot supply setup competence, given whole-trajectory PPO, short horizons, no use check, and puzzles scored with history off.
- **Tests:**
  - #98, #99: 009-pilot-hist4 (cold): +22.6 [-3.3, 48.8] at 250; at 260 competence 0.421 vs 0.437 (bar 0.06), Elo +0.2 [-12.1, 12.4]; puzzles ran history 0 in 2 of 5 parts. (null)
  - #99: 009-pilot-memattn (zero-init mem_out) forked at 250: -18.3 Elo [-31.0, -5.6] after 1,600 games; stopped after one segment. (worse on Elo; competence unmeasured)
  - #100, #103: 009-pilot-memgru: -10.3 [-22.3, 1.8] at 270, -21.2 [-34.2, -8.3] at 280; no ONNX export, s1 card error. (worse on Elo; competence unmeasured)
  - #76: memory_reach on untrained smoke pilots: GRU gradient 0.52 at lag 1 -> 0.001 at lag 16; attn 0.017 -> 0.0075. (diagnostic)
  - #76, #79: Designed screen hist4/gru/attn, 2 seeds, 80 iterations (runs/memory_run.sh) parked and never ran. (untested)
  - #94: Fixed metagame.py so game workers get the history window; earlier in-loop history pilots saw no history. (infrastructure)
- **Do not repeat:**
  - 009-pilot-hist4: history tokens W=4 grown cold onto the main line at 240, 2 segments, decided on s1 at 260
  - 009-pilot-memattn: attention memory over own decisions, zero-init mem_out, forked at 250, stopped after 1 segment
  - 009-pilot-memgru: GRU memory, zero-init, forked at 260, 2 segments, -21.2 Elo at 280
  - Deciding any memory pilot on s1 without history/memory support in the ONNX puzzle path
- **Untested variants:**
  - #76's own screen: hist4 / gru / attn, 2 seeds, 80 iterations, memory_reach after training. *Distinct:* Two seeds and 4-8x longer than the lab branches. *Cost:* high
  - memory_reach on the trained memattn and memgru branches. *Distinct:* Separates 'memory useless' from 'memory never learned'. *Cost:* low
  - Control with whole-trajectory PPO minibatches and the memory core off. *Distinct:* Isolates the PPO-procedure confound behind the -18 and -21 Elo. *Cost:* medium
  - hist4 warm-started through rl/warmstart.py. *Distinct:* Removes hist4's non-identity growth handicap. *Cost:* medium
  - Any memory form on the adopted deck-free (deck_mode cross) pilot from 290 on. *Distinct:* Memory of revealed opponent cards and own draws may carry information the deck-free board lacks. *Cost:* medium
  - Re-score hist4 competence with the puzzles' TokenEncoder history set to 4. *Distinct:* Measurement fix needed before any competence claim stands. *Cost:* low
  - Recurrent-PPO literature lookup (truncated BPTT with burn-in, stored hidden states, updates needed before memory is used). *Distinct:* Would say whether 10-20 iterations was ever a fair test. *Cost:* low

### H60 · N11, N9 · adopted (weak) · Deck-free board encoder with deck cross-attention

**Evan:** his idea (rule 4: tried first and fully).

- **Mechanism:** A deck-free board encoding fused with the deck by cross-attention should generalise across decks; a distilled warm start removes the cold-start handicap.
- **Verdict:** Adopted at 290 on one warm-started fork (009-pilot-deckcross-w: +36.6, +20.9, +34.9 Elo sequential; archived gate +5.4 [-11.6, 22.4]), so at least as strong on drafted decks, confounded by the distillation refit, +33% parameters and the branch's own population. 'Better Trainer play' is unsupported but not refuted: every competence reading sits inside the 0.06 A/A bar, and the human-shaped population it brought collapsed within 13 iterations (#109).
- **Tests:**
  - #73, #74, #75: 40-it screen: vs base 0.490 / 0.470, Elo -3.6 / -14.2; weakest vs pilot-v2 at it19 (0.203); SimpleBot archived 0.278 vs base 0.301, no-deck 0.376. (inconclusive)
  - #94, #98: Grown deck-blind: -54.3 Elo [-77.5, -31.5] after 400 games; one-iteration fork value loss 0.292 vs 0.087-0.122. (inconclusive (handicap))
  - #98: Warm start 40 games/1 epoch: value MSE 0.290 -> 0.878; 400 games/2 epochs worked (KL 0.155, agreement 0.770). (protocol)
  - #100, #101, #105: +36.6 at 270, +20.9 [0.8, 41.1] at 280, +34.9 [15.8, 54.1] at 290; archived +5.4 [-11.6, 22.4] over 1,104 games; one fork. (adopted)
  - #104, #109: Branch population 28 Trainers, distance 10.5 vs 20.5 at 280; collapsed to 33/8/20 within 13 iterations after adoption. (shape claim retracted)
  - #108, #110, #116: Competence 0.480 (280), 0.496 (310), 0.472 (320), 0.447 (360); Trainer-first 0.577 -> 0.680 -> 0.557; all inside 0.06 bar. (inconclusive)
  - #112: Two forks of the deck-free state at 300 diverged (lr 1e-4 collapsed, lr2 held 23-29 Trainers). (single-fork shape unreliable)
  - #117, #132: From-scratch runs with deck_mode cross collapsed into Pokemon piles. (does not stop F5)
- **Do not repeat:**
  - deck-cross grown deck-blind (cold, ZERO_AT_GROWTH fusion) and judged after one segment (#98: -54.3 Elo)
  - Single-seed 40-iteration from-scratch architecture screens whose ladders resample deck pairs (#74: ±15 Elo rerun, 6-20 Elo seed noise)
  - Warm-start distillation with ~40 games and 1 epoch (#98); use 400+ games and 2+ epochs
  - Reading a single fork's population deck shape as evidence for a pilot architecture (#104 retracted by #109/#112)
- **Untested variants:**
  - Self-distillation control: warm-start a joint-architecture student by the same rl/warmstart.py procedure and fork it beside the main line. *Distinct:* Separates architecture from the refit; needed to attribute the +35 Elo. *Cost:* medium
  - Decklist dropout in training (#73/#74 Next). *Distinct:* Makes the board stream stand alone; regularisation, not a new path. *Cost:* low
  - Decklist overfitting check: same ladder on training vs held-out decks (#73/#74 Next). *Distinct:* Tests the generalisation half of the mechanism. *Cost:* low
  - Draft head reading the deck encoder's output directly (#72 Next). *Distinct:* Changes the meta-level representation, not the pilot. *Cost:* medium
  - Deck-cross pilot trained on pilot-v2's recipe (wide random decks, deck-out wins 0), as diagnostic. *Distinct:* Tests whether architecture relates to the wall-favouring verdict bias (F2), since pilot-v2 differs in both architecture and data. *Cost:* high
  - Second fork or more seeds of deckcross-w (#72 Next: 80 iterations, two seeds). *Distinct:* Replication only. *Cost:* medium
  - deck_layers > 1 or interleave on the main line. *Distinct:* Different fusion depth; interleave only screened from scratch (#73, -15 Elo, +82% params). Minor variant. *Cost:* medium
- **New hypotheses (section 6):** H77, H91

## N12 · Measurement

### H61 · N12 · partly-supported (strong) · SimpleBot is a valid yardstick

- **Mechanism:** A scripted bot with a one-step Item rule gives a transitive ladder that separates weak pilots from competent ones, but it cannot value setup Trainers such as PlusPower and Gust, so it rewards Energy.
- **Verdict:** SimpleBot is refuted as a measure of deck or Trainer value. Its card ablations (#32, #92), its Energy-to-Trainer swap (#68) and its both-sides panel (#85-#126, peaking at 0.704 at 28.5 Energy and 0.685 at 36.5 Energy) all favour Energy over Trainers, the opposite of the human lists, so it holds only as a coarse strength floor (#49, #74, #124), and own-deck-vs-SimpleBot has been saturated at 0.93-0.98 since about iteration 200.
- **Tests:**
  - #8, #12: vs random 96.9% +/-3.5 (#8), 99.8% (#12); vs first-option 96.8%; vs heuristic 61.4% +/-4.8; 400 games a pair, 24 decks; ladder transitive (supported (transitive among weak bots only; says nothing about deck value))
  - #17: 24x24 matrix over the human lists, 27,600 games; Nash Sponge 0.469 / Wigglytuff 0.406 / Articuno-Hitmonchan-Scyther 0.125; no Haymaker in support (best -0.17) (against (SimpleBot's meta differs from the human one))
  - #24: Answer key on SimpleBot's Nash: 6 of 7 staples played; Item Finder missing (mixed)
  - #32: One copy swapped for basic Energy: PlusPower 40.1 +/-2.2, Item Finder 43.2, Gust 43.7, Computer Search 44.5, Oak 48.9, DCE 51.7 (refuted (Trainer value))
  - #33: Own vs SimpleBot 93.0% (R=0) vs 95.5% (control); pilots with different ending mixes look the same (weakened (early saturation))
  - #49, #74: Archived lists: 40-iteration pilots 0.30-0.34, pilot-v2 0.817, gae1 0.085, meta-99 0.724; rerun and seed noise as large as architecture effects (supported (strength floor only))
  - #50: psearch beats its own greedy pilot 65.4% but gains nothing vs SimpleBot (82.5% vs 81.7%) (weakened (strength half))
  - #63: Own deck vs SimpleBot at round 19 vs cross-play strength r = -0.06; 21 agents; own-deck score mixes pilot-deck fit (refuted (as a tournament-strength measure; low power, confounded))
  - #68: Swapping ~4 basic Energy for Bill/Oak/Computer Search drops best decks 0.475 -> 0.385 under SimpleBot (200 games a deck) (consistent with SimpleBot's anti-Trainer bias)
  - #85: First SimpleBot-both-sides panel: meta-99's Trainer-light best decks beat the human lists 0.467/0.621/0.579 at iterations 49/99/149 (refuted (deck value))
  - #86, #89, #101, #110: Panel 0.532 (160), 0.588 (200), 0.616 (280), 0.532 (320); own vs SimpleBot 0.902-0.947 (refuted (deck value))
  - #92: Human lists with all Trainers turned to basic Energy score 0.433 (SimpleBot prefers them); search/disrupt/tempo 0.379/0.397/0.333, draw 0.490, below every learned pilot (refuted (Trainer value))
  - #114, #115, #119, #126: Panel 0.668 (360), 0.704 (400, 28.5 Energy), 0.685 (440, 36.5 Energy); own vs SimpleBot 0.971-0.978; #114's 'fairer answer key' overturned (refuted (decisive))
  - #124: From-scratch Pokemon piles score 0.089 with SimpleBot on both sides (supported (floor flags degenerate decks))
- **Do not repeat:**
  - Using the SimpleBot-both-sides archived panel (sb_archived_mean) as a fitness, adoption or human-likeness signal: it scores 36.5-Energy walls 0.685-0.704 against the human lists (#119, #126)
  - Using own-deck-vs-SimpleBot to rank pilots or decks: uncorrelated with cross-play (#63), saturated at 0.93-0.98 since about iteration 200 (#101-#126)
  - Rerunning SimpleBot card or group ablations (#32, #92) or Energy-to-Trainer swaps under SimpleBot (#68) as evidence about Trainer value
  - Citing #114's 'the SimpleBot panel is the fairer answer key' without #119 and #126
- **Untested variants:**
  - [outside research] 2000-era players or transcribed 2000-era games as an evaluation yardstick. *Distinct:* The only yardstick not built in this system; no attempt in the log, evan-requests or README. Evaluation only under Rule 1; first check whether usable period records exist. *Cost:* deep research (uncertain feasibility)
  - Fixed search-strength evaluation panel (parked search rung #13 with many more rollouts, or #148's one-turn determinized search on both seats), which should score the human field near 0.5 and the walls below 0.5. *Distinct:* Unlike SimpleBot it can value setup Trainers (one-turn search lifts PlusPower puzzles from 31% to 81%); --judge-search is used as a judge, but no fixed search evaluation panel is recorded. *Cost:* medium
  - SimpleBot with a turn-level Item rule that scores Item+attack sequences. *Distinct:* Directly tests whether #92's explanation (one-step Item rule) accounts for its Energy preference; hand-written bot, so evaluation only. *Cost:* low
- **New hypotheses (section 6):** H71

### H62 · N12 · weakened (strong) · Short screens and lab forks can rank pilot changes

**Evan:** his idea (rule 4: tried first and fully).

- **Mechanism:** Between-fork training noise swamps small pilot effects in one-segment forks: sigma is ~8.8 Elo from two A/A cards and likely 15-20 Elo after the later recipe changes.
- **Verdict:** One-segment lab forks reliably flag pilot effects of about 35 Elo or more (deckcross-w +36.6/+20.9/+34.9, KL anchor ~65, exit-strong -78.6, cold slotbind -201.4), but they cannot rank effects under about 20-30 Elo, and single-fork passes near elo1 20 can be false (#90 +29.6, replication #97 +0.0). Untested: whether replicated, paired (common random numbers) or recalibrated forks could rank small changes; the A/A bar rests on two cards at iteration 160.
- **Tests:**
  - #70: Ablation chain redirected at Evan's suggestion (#71); base finished 80 iterations, base-s2 kept as seed-noise floor; nine ablations never started (abandoned/redirected)
  - #73: First ladder: base vs base-s2 0.475 +/-0.049; no-deck's it19 lead later shown to be noise (#74) (noise floor)
  - #74: Same snapshots between ladders: base-s2 -0.6 -> +14.2, deck-cross -3.6 -> -14.2; deck pairs resampled per ladder; fixed pairs adopted (#76) (refuted (unpaired ladders only))
  - #78, #82: ~12 from-scratch changes did not separate; base still learning (+55 Elo, +9.6 vs SimpleBot over 40 more iterations); explore10 0.463 vs 0.372 at it19, 0.539 vs 0.616 at it79 (refuted (short from-scratch screens; curves cross))
  - #83, #86: Two A/A cards: sigma ~8.8 Elo, reseeded no-change -13.3; forks are not common random numbers; sigma's upper bound roughly 6x (calibration only (n=2))
  - #87: 2-epoch fork +40.5 [22.4, 58.8] after one segment; single fork, adopted as noninferior (supported (large effect))
  - #88: aux card +15.6 at 180, then -22.6 at 190; SPRT stops at its first 100-pair look (refuted (small effects))
  - #90, #97: Meta-only card (no pilot change) passed pilot gate +29.6 [18.6, 40.7]; replication +0.0 [-11.3, 11.3] (false positive above elo1 20)
  - #96: Competence A/A at 160: differences -0.035/+0.006, RMS 0.025, bar 0.06; spread mostly 16 PlusPower puzzles (calibration only)
  - #98, #99: hist4 +22.6 [-3.3, 48.8] at 250, then +0.2 at 260; cold deck-cross -54.3 measured the deck-blind start (noise)
  - #100, #105: deckcross-w +36.6, +20.9, +34.9 across three segments; adopted (supported (large effect))
  - #103, #106: exit-strong -78.6, exit -56.1, exit-h2 -36.6, lamturn -37.1, shapeon -31.4, cold slotbind -201.4 after one segment (supported (large negatives))
  - #108, #110: Trainer-first competence 0.680 at 310, then 0.557 at 320 (noise)
  - #111: lr2 accepted H1 at +13.8 [4.3, 23.3] after 2,400 games, below elo1, adopted; competence not measured (unreplicated)
  - #102, #112: Shape A/A RMS 7.83 (bar 16); two forks of one state diverged 27 vs 8 Trainers within 12 iterations (meta-side fork noise)
  - #113: deep6 +14.3 [-3.7, 32.4] at 320 from 310 fork (lr 1e-4), then -25.2 [-41.6, -9.0] from rebased fork (refuted (noisy; confounded by learning rate))
  - #116: None of 16 pilot cards moved competence by its 0.06 bar; stall rule triggered (insensitive)
  - #127: Pilot gate measured on decks from two one-type populations rewards the trap (confounded (measurement validity))
  - #137, #138: h2h seed 0 vs 1 differ 4-11 Elo; control scr-resetent +30.0 -> +25.2 -> +2.8; anchor separated ~65-70 Elo in 12 iterations vs matched control (supported (large effect))
- **Do not repeat:**
  - One-seed 40-iteration from-scratch screens judged on ladders with resampled deck pairs (#73, #74, #78)
  - Deciding a pilot card from one fork at elo1 20 with the SPRT stopping at its first 100-pair look, then reading a rejection as 'no effect' (#88)
  - Adopting on a single-fork pilot-gate gain of 20-35 Elo without replication (#90 +29.6 -> #97 +0.0)
  - Using thresholds (sigma, s1 bar 0.06, shape bar 16) from the two A/A cards at 160 after the recipe changed (2 epochs, lr 2e-4, deck-free encoder)
  - Ladders that resample deck pairs per run (#74)
  - One-segment early stops for changes that cannot start as the identity, without a warm start (#98 deck-cross -54.3, #106 slotbind -201.4)
  - Single competence readings, dominated by 16 PlusPower puzzles, as evidence of change (#108 -> #110)
  - Pilot gates measured only on decks from one-type populations (#127)
- **Untested variants:**
  - Paired forks with common random numbers (seeded workers, fixed collection order, deterministic CUDA). *Distinct:* Lowers between-fork noise rather than measuring it; #83 shows forks diverge from the first iteration (3,189/2,995/3,592 transitions). *Cost:* medium (determinism engineering, not research)
  - [outside research] Truncated-curve ranking robust to crossing curves (learning-curve extrapolation, freeze-thaw style). *Distinct:* Ranks from partial curves; untested, but the record argues against naive versions (#82 curves cross; pilot-v2 gained most between it99 and it199, #78). *Cost:* deep research
  - k = 3-5 replicate forks per lab card with a pooled test. *Distinct:* Only 006 was ever replicated; replication directly addresses false passes like #90. *Cost:* medium
  - Recalibrating the A/A after each adoption with more than two cards. *Distinct:* Current bars predate four recipe adoptions; later swings imply sigma ~15-20 Elo. *Cost:* low-medium
  - Judging pilot cards on a fixed type-diverse or human panel with a search-strength judge (--judge-search). *Distinct:* Removes the one-type-population validity confound of #127. *Cost:* medium
- **New hypotheses (section 6):** H74, H98

### H63 · N12 · refuted (strong) · The answer key under the shared pilot measures rediscovery

- **Mechanism:** Win rate against the human lists under a judge pilot is shape-blind and co-adapted: it rewards whatever the judge plays well, not closeness to the human decks.
- **Verdict:** Refuted as a sufficient progress metric. The answer key rises while decks leave the human shape under every judge tried (shared pilot #90/#101, pilot-v2 #89, SimpleBot #119/#126 at 0.685 with 36.5 Energy), and the walls' score follows their own pilot (0.720 vs 0.237, #137/#147); it does catch gross collapse (#91, #124 piles at 0.0375), so it remains a floor only.
- **Tests:**
  - #86, #90: Main-line key 0.7191 (160) -> 0.794 (210) while staples 4.83 -> 3.42, best overlap 0.533 -> 0.45; drops equal the A/A spread (1.4 staples, 0.08 overlap) (refuted (weak alone))
  - #101: 008b key 0.766 vs main 0.717 (+0.049, rule 0.03) with best-deck shape 19.2/10.3/30.4 vs 15.4/19.3/25.2; single fork (refuted (key passes a wrong-way card))
  - #85: SimpleBot-both-sides key and pilot-v2 key order snapshots differently; pilot-v2 rates the Trainer-lighter meta (149) higher (refuted (judge-dependent))
  - #89: Pilot-v2 key 0.48 -> 0.68 (160 -> 200) while best decks moved to 20.2/10.9/28.9 and staples fell 4.83 -> 4.17 (refuted)
  - #91: 007's key gain +0.128 mostly from main line's fall 0.794 -> 0.695 as its median Trainers collapsed to 2-3 (partial counterexample (tracks extreme collapse))
  - #102: Shape gate added because the key alone passed 008b; shape A/A RMS 7.83, bar 16 (refuted)
  - #118: draftlr3 adopted with key +0.009 and shape 14.7 vs 15.8; shows no harm, not progress (uninformative)
  - #119, #126: SimpleBot key 0.704 at 400 (distance 20.5, 28.5 Energy), 0.685 at 440 (36.5 Energy) (refuted)
  - #124: From-scratch Pokemon piles score a key of 0.0375 (supported (floor))
  - #137, #147: Walls' pilot / human lists' pilot: own/own 0.720, own/v2 0.761, v2/v2 0.237, v2/own 0.233; all 10 population pilots rate walls 0.68-0.75 (refuted (co-adaptation))
  - #144: Review analogues: JPC-style loss ~0.68 (walls 0.74 -> 0.235); shared-weight NAS ranking Kendall tau near 0 (supports refutation)
- **Do not repeat:**
  - Deciding meta cards on the answer key alone, under any judge, without the shape gate (#101, #102)
  - Swapping the key's judge to pilot-v2 or SimpleBot and treating that as a fix (#85, #89, #119, #126)
  - Reading staples or best whole-list overlap from a single fork as evidence: A/A spread 1.4 staples and 0.08 overlap (#86); whole-list overlap cannot tell archetypes apart (#120)
  - Counting a branch's key gain as progress without checking whether the control collapsed (#91)
- **Untested variants:**
  - Key under search-strength play on both seats with a 50-60 turn draw limit, tracked over snapshots as a lab metric. *Distinct:* Changes the judge's competence and the payoff; #147 tested it only on 3 walls at one point (0.44-0.46); #148 judge-search work is uncommitted with no log entry. *Cost:* medium
  - Cross-play key with JPC-style decorrelation: decks judged by a held-out pilot from a different screen, scoring the off-diagonal average. *Distinct:* Removes judge-deck co-adaptation; #137 is a one-off diagnostic, never a tracked metric. *Cost:* medium
  - [outside research] Evaluating designs with a biased or co-adapted evaluator (unbiased or held-out evaluators, ranking correlation under weight sharing beyond #144), or a much stronger independently trained judge. *Distinct:* Every internal judge plays the human lists far below human level (#116, #137), so no internal key can certify rediscovery. *Cost:* deep research

### H64 · N12 · refuted (strong) · Shape distance and type count capture the gap

- **Mechanism:** Distance to 13.5/28/18 ignores which cards are played (special Energy counts as Energy), and the Pokemon-overlap type count splits walls carrying extra Pokemon into small types.
- **Verdict:** Refuted as a sufficient criterion. Small shape distance with several types coexisted with walls in #114 (11.5 inside one Chansey/Snorlax type), #132 (45 types, largest 48 C/S decks), #140 (73 of 99 C/S) and #146 (largest type 22 with 75 of 99 C/S; distance 9.7 with 70 of 99), and in #63 with a different type metric; both metrics remain valid only as necessary-condition detectors of floods (#110 distance 38).
- **Tests:**
  - #102: Shape A/A at 160: +10.5 and +3.5 (RMS 7.83), bar 16; later screen A/A RMS 2.58, 001-aa-same vs main RMS 4.79 (calibrated (regime-dependent))
  - #120: Pokemon-overlap gives human lists 3 types + 4 singletons (whole-list overlap: 20 of 24 in one type); main line 1 type at 160-400 (2 at 290) (partly supported (3 types vs 8 archetypes))
  - #129: Threshold-sensitive: human lists 9/7/4 + 4 singletons at 0.5, 10/9/2 at 0.4 (weakened)
  - offline synthesis (ledger cited '#140, DATA'): Top-12 holding Chansey/Snorlax 9-12 across screens (11-12 from 484 on); pooled within-run r(distance, largest type) 0.24 over 72 rows (metrics differ (not by itself a refutation))
  - #140: 73 of 99 decks hold Chansey and Snorlax (control 79); gate type sizes 15/12/26/23; best decks 6-12 cards off inside walls (refuted)
  - #146: league479 largest type 22 at 499 with 75 of 99 C/S decks; gatevs479 distance 9.7 with 70 of 99 (refuted)
  - #114: Distance 11.5 (8/29/23) but all 12 best decks one C/S wall type on 17 Psychic Energy; pilot-v2 rates them 0.24-0.30 (refuted (distance))
  - #119: Same type swapped 7 Trainers for Potion and Full Heal special Energy; distance rose only to 20.5 (refuted (shape blind to cards))
  - #132: 45 types at 483 while largest type held 48 C/S decks; best decks 11-14 cards off inside the wall type (refuted)
  - #63: Distinct types in all 84 run-rounds (closest pair at least 34 cards) but decks 29.0/5.3/25.6, 0 of 8 archetypes at 50% overlap (refuted (different type metric))
  - #110: Distance 38 at 320 tracked the collapse into Colorless Pokemon (supported (necessary condition))
- **Do not repeat:**
  - Deciding a meta or league card on the Pokemon-overlap type count alone (e.g. 017's rule 'at least 1 more deck type than the main line'), or reading a smaller largest type in gate or league screens as diversity, without a core-card check (#140, #146)
  - Reading top-12 shape distance near or below the A/A bar as human-likeness without a card-level or archetype check (#114: 11.5 inside walls; #140: 6-12 inside walls)
  - Using whole-list overlap (archetypes_at_half) to count types (#120)
  - Using logged `types` rows (pre-turnover, last head only) as type-size evidence for multi-head runs (#143)
- **Untested variants:**
  - Game-agnostic core-card share: share of top decks holding the population's modal k core cards, used as a gate (and as the trigger instead of the hand-picked Chansey/Snorlax count). *Distinct:* Ad hoc C/S counts exist (#140, #146) but are game-specific; a general version sees convergence the type count misses. *Cost:* low
  - Card-level (not Pokemon-only) clustering with the threshold calibrated on the 24 human lists. *Distinct:* Fixes #129's threshold sensitivity and #120's 3-types-for-8-archetypes gap. *Cost:* low
  - Matchup-matrix effective rank under pilot-v2 or search play, compared with the human field's own matrix. *Distinct:* Measures strategic rather than card diversity; untested in this loop (related equilibrium measures in #57, #63); must avoid the shared-pilot bias. *Cost:* medium
  - Card-identity distance to the nearest human archetype (card-multiset L1 or earth-mover distance with Energy split by type and special vs basic). *Distinct:* Catches #119-style special-Energy swaps that the shape metric misses. *Cost:* low
- **New hypotheses (section 6):** H113

### H65 · N12 · inconclusive (weak) · The competence score measures Trainer play

- **Mechanism:** s1 averages the search/disrupt/tempo Trainer-value groups on the archived lists with the Trainer-first and PlusPower-only lethal puzzle classes, and it leaves out the draw group and the all-Trainers column.
- **Verdict:** The competence score's noise is calibrated (A/A RMS 0.025, bar 0.06, from n=2), but its validity as a measure of Trainer play is not shown. A pilot trained on the human lists scores only about +0.02 on its components (#92), a Trainer-first lean that lost 78.6 Elo raised its puzzle part (#103), it stayed flat while the deck-free encoder gained +35 Elo (0.480 -> 0.496), and its movements come mostly from the 16 PlusPower puzzles.
- **Tests:**
  - #96: A/A at 160: main 0.434, 001-aa-same 0.398, 002-aa-reseed 0.439; differences -0.035/+0.006, RMS 0.025, bar 0.06; spread mostly PlusPower puzzles (calibration only)
  - #101: 0.437 (260) -> 0.480 (280), almost all PlusPower 6 -> 9 of 16; Trainer groups flat; then 0.472 (320), 0.447 (360) (within noise; did not hold)
  - #92: s1 components: a4-tok ~0.462, main 0.441 (220), pilot-v2 ~0.427; Trainer-first 60/58/61%, PlusPower 31% for all three (against validity (no positive-control separation))
  - #103: exit-strong raised Trainer-first 0.577 -> 0.680 yet lost 78.6 Elo; its s1 0.442 vs 0.480 (against validity)
  - #108, #110: Entropy 0.02: groups +0.02-0.05, puzzles down similarly, s1 net -0.005; Trainer-first 0.680 at 310, 0.557 at 320 (noise)
  - #106, #111, #113, #116: No pilot card moved s1 by 0.06; deck-free (+35 Elo) s1 0.480 -> 0.496; lr2 (+14 Elo) s1 never measured (unresolved (insensitive or pilot flat))
  - #99, #116: hist4 at 260 s1 0.421 vs 0.437 (-0.016); slotbind-w at 360 0.460 vs 0.447 (+0.013) (below bar)
  - #114, #119, #126: s1 0.447/0.460/0.483 at 360/400/440; Trainer-first 0.577/0.608/0.639; Trainer rows flat while decks went to 29 Trainers (within noise)
  - #96 (table), #92(4): psearch k4/k8 lifts puzzles 79.2% -> 89-90%, Trainer-first 60 -> 85-88%; Trainer-value groups never measured under search (supported (puzzle half only))
  - #104: lab.json held stale s1_min_gain 0.03 from ~14:53 to 22:13 restore; hist4 -0.016 fails either bar (no decision affected)
  - #137, #138: scr-resetcap pilot ~20 Elo and KL-anchored pilot ~65 Elo better than pilot-v2 on human lists; s1 never measured on either (positive control not run)
- **Do not repeat:**
  - Setting the competence bar from only two A/A forks (n=2 differences) while the PlusPower class (16 puzzles, 1/5 weight) dominates the spread (#96)
  - Reading a single-milestone s1 or Trainer-first change below 0.06 as movement (#108 -> #110: 0.680 -> 0.557)
  - Raising the puzzle part through distilled one-turn search targets, which inflates Trainer-first puzzles while costing 37-79 Elo (#103, #105, #106)
  - Treating pilot cards adopted for drafted-deck Elo (deck-free, lr2) as evidence about Trainer competence without measuring s1 (#111, #116)
- **Untested variants:**
  - More puzzles per class (beyond the 408 of #92: 16 PlusPower-only, 97 Trainer-first). *Distinct:* Reliability fix: lowers per-puzzle weight (~0.0125) and A/A variance; does not test validity. *Cost:* low
  - Positive-control validation: full s1 for a4-tok, arch-A, pilot-v2, the KL-anchored pilot (+65 Elo, #138) and scr-resetcap's pilot. *Distinct:* Tests construct validity, not noise; #92 has partial component data only (~+0.02 for a4-tok). *Cost:* low
  - Trainer-value groups under play-time search (psearch). *Distinct:* Only the puzzles were measured under search (#96); checks whether the panel half responds to a known improvement. *Cost:* low-medium
  - 3 or more A/A forks with a bar set per component instead of one composite bar. *Distinct:* Also covers the 64-game-a-pair panel groups, unlike more puzzles. *Cost:* medium
  - Include the draw group and all-Trainers columns, or weight components by sample size. *Distinct:* Changes what is measured: those columns separate a human-list-trained pilot most (#92: all 0.789 vs 0.672). *Cost:* low
  - [outside research] Validating a playing-skill metric (positive/negative controls, item-response or psychometric reliability, ablation-panel power). *Distinct:* A measurement-design question, not RL; the stall rule (#116) fired on an unvalidated score. *Cost:* deep research
- **New hypotheses (section 6):** H79

### H66 · N12 · partly-supported (strong) · Bookkeeping bugs and machine kills changed verdicts

- **Mechanism:** Machine sleep, shutdown, OOM and code bugs end or corrupt runs independently of merit, which leaves verdicts undecided or underpowered rather than flipped.
- **Verdict:** Supported in this form: process faults truncated or mis-measured experiments. 017-meta-league3-m, 019-meta-select and 019-meta-select-floor (#128), scr-resetent10 and scr-practice1k (#136) were never decided, scr-anchor's deck verdict rests on 12 iterations (#137/#138), the #72/#74 screen was halved to 40 iterations, and #43's deck counts, the #112 milestone and the #62 loop games were mis-measured. Not shown: that any lab bookkeeping bug (#86, #87, #104, #107) flipped a final verdict; #108 redid #107's card to the same failure.
- **Tests:**
  - #46: #43 counted any 'Energy'-named card as Energy; seed-3 novelty deck 15/24/21, not 10/24/26; replication verdict driven by seed luck, unchanged (supported (mis-measured shape))
  - #86, #87: Restart bug and retest copy dropping 'test' caught before acting ('would have been'); epochs-2 contamination prevented by hand rebase (no verdict changed)
  - #107, #108: ent02-b failed at 310 by the wrong (Elo) rule; redone on competence 0.491 vs 0.496 (-0.005, bar 0.06), failed again (no verdict changed)
  - #94: History window never passed to metagame workers; fixed before any history pilot ran in the loop (latent, no effect)
  - #104: adopt() wrote stale s1_min_gain 0.03 over 0.06; card-copy race; lab died with its session at 22:10; no decision depended on it (no verdict changed)
  - #112 (ledger cited #110): adopt() copied 032-pilot-lr2 state over main/seg_0320.pt; #110 milestone (key 0.34, distance 38) described a replaced line (supported (interpretation changed))
  - #128: 019 cards and main line died 23:05:50 (failed shutdown, event 1073); screens 23:27 (sleep, event 42); 017-m (at 453, due 480), 019 cards (due 490) never decided (supported (truncated))
  - #77: Chain stopped when PC slept at 00:24 on 10-15 (Kernel-Power 187); base79-head credit probe skipped (supported (truncated))
  - #111, #118, #121, #122: Three CUDA OOMs at micro-batch 512 under 5.30 GB cap (deep8, 016-scratch-recipe, 017-meta-league3), requeued at 256; auto fallback added; two started late (delayed)
  - #136: Low system memory stopped scr-resetent10 (--draft-ent 0.1) and scr-practice1k (--practice-games 1000) shortly after start; never rerun (supported (truncated))
  - #31: Three crashes or hangs 10-04 to 10-06 (bugcheck 0x20001 during #32 ablations, two sleep hangs); origin of the 80% load cap (supported)
  - #43: Proposal-count loop bug (8 decks an iteration) forced reruns; rerun 'both' dropped no-op swaps, head arm did not; position-dependent deals, score s.d. 0.018-0.026 (supported (mis-measured, confounded))
  - #48: pilot-v2 stopped at iteration 371 of 400, cause unrecorded; its diagnostics and count-features-only run never ran (supported (truncated))
  - #52: Rattata TR and Dark Gyarados TR card bugs crashed games; hidden from earlier experiments by the field pool (engine fault)
  - #62: Dark Dragonair TR free cycle sent 23-28 of 96 greedy tournament games to the 5,000-step cap; N=3 run discarded, chain restarted (supported (mis-measured, rerun))
  - #72, #74: #71 screen killed by overnight shutdown; cand-self and ability-text rerun at 40 not 80 iterations, judged 'within noise' (supported (underpowered))
  - #101: Claude killed the lab's process tree to stop adoption of 008b-meta-practice10, which had passed its rule; shape gate added after (manual intervention on merit)
  - #103: 009-pilot-memgru recorded as error (no ONNX export for puzzles); Elo gate -21.2 anyway (verdict stands)
  - #133: Shutdown lost #127's queued pilot-v2 head-to-head on the human lists; restarted later (delayed)
  - #137, #138: scr-anchor crashed at 464 (TypeError: 'float' object is not callable), resumed 08:27, stopped 472; anchor + gate + varied-field stack never ran (supported (truncated))
  - #141: Challenger-practice smoke test CUDA OOM at iteration 481 (1.6 GB share beside three screens) (truncated)
- **Do not repeat:**
  - Starting the lab or long chains from a session shell without rl.lab start (CREATE_BREAKAWAY_FROM_JOB): the process dies with the session (#104)
  - Running long overnight runs while the PC may be shut down or put to sleep (#72, #77, #128)
  - Lab or screen runs at micro-batch 512 under a 5.30 GB cap on decks with many Pokemon without the #122 OOM fallback (#111, #118, #121)
  - Four or more screens at once, or a 1,000-practice-game screen beside three others (#136: system RAM exhausted)
  - Hand edits to lab.json or cards while the lab process runs on code loaded before the edit (#104, #128)
  - Reading a milestone taken at an adoption boundary as the continuing main line (#112)
- **Untested variants:**
  - 017-meta-league3-m (fresh league of 3 draft heads) decided to 480. *Distinct:* Fault-truncated (#128), never resumed; 'league of fresh heads' rests only on per-head reads over 400-429 (#121/#123/#125). *Cost:* medium
  - 019-meta-select and 019-meta-select-floor decided in the lab at 490. *Distinct:* Noise-aware select inside the lab, killed at #128 and never decided. *Cost:* medium
  - scr-resetent10 (--draft-ent 0.1, 250 practice games) run to 500. *Distinct:* Stronger draft entropy bonus; stopped by low memory (#136), never rerun. *Cost:* medium
  - scr-practice1k (--practice-games 1000) run to 500. *Distinct:* Larger practice dose; stopped by low memory (#136), never rerun. *Cost:* medium
  - scr-anchor beyond 472, and the anchor + select-z gate + type-capped varied field stack named in #138 Next. *Distinct:* KL anchor run long enough for decks to respond; the 12-iteration verdict was cut by a crash. *Cost:* medium
  - cand-self and ability-text at the original 80-iteration budget (#71 plan). *Distinct:* Cut to 40 iterations by a shutdown (#72/#74); 'within noise' verdict underpowered. *Cost:* medium
  - pilot-v2 trained to its planned 400 iterations, and the count-features-only pilot (#48). *Distinct:* Stopped at 371 with cause unrecorded; isolates the count-encoding cause never tested. *Cost:* medium

## N13 · Proxy deck objectives

### H67 · N13 · refuted (strong) · The pilot's start-of-game value as deck objective

- **Mechanism:** A value head calibrated on fixed decks overrates the out-of-distribution Energy-heavy decks a search finds (surrogate over-exploitation), and the opening reading itself misranks Trainer variants.
- **Verdict:** Searching the pilot's start-of-game value drove decks to 29-36 Energy with few Trainers in about 15 runs (#34, #40, #43, #46, #47, #53, #57, #63) under four kinds of pilot: result #1's human-trained pilot, the scratch pilot, co-trained pilot-v2 with count features, and per-agent pilot-v2 copies. Harder optimisation made real decks worse (#43, #46, #47). Not shown: #36's full Trainer-variant reversal under any pilot other than result #1's deck-out-biased one, and whether count encoding alone causes the bias (#48's count-features-only run never ran).
- **Tests:**
  - #34, #35: Value builder 50.3% vs archived field; 643,164 vs 1,404 candidates (458x); Graham's Haymaker 0.767 overlap, 34 vs 22 Energy; 0 Nash weight; one seed, 60 games a pair (mixed (beats builders, not human-like))
  - #36: Value 0.560/0.518/0.477/0.502 vs real 0.499/0.576/0.632/0.681; first three exact reverse; Energy 17.4 -> 30.4; result #1's pilot only (refuted)
  - #37: Value weakest matchup-model input (held-out MAE 0.236, rank +0.27); ranks #36 variants -0.20; raw value 0.663/0.625/0.634/0.637 puts 34-Energy deck first (refuted)
  - #38: Start-of-game value weight -0.19, turn-5 in-play value +0.43; start value 0.325/0.253/0.262/0.270 as real strength rises (refuted)
  - #39: Value's deck 49.7% vs field, beats strength's mixture 90.2%; 'finds good basins fast but misranks within them' (mixed)
  - #40: Closed-loop value PSRO 60.7% vs field under shared pilot; proposals 22.5 -> 31.8 Energy; co-adaptation 11 points (refuted (human-likeness))
  - #41: Temperature 0.03 kept 19-25 Energy and Trainer packages but weaker (32.9% vs 60.7%) (mixed)
  - #42: Scratch pilot's value calibrated on four hand-made variants but flat (2 vs 18 points) (inconclusive alone)
  - #43: Scratch pilot: attractor still Pokemon pile 34+ Energy (base 20/6/34, head 21/4/35); edit head worse (55.3% vs 47.3%); count embedding never trained (refuted)
  - #46: Seeds 3-5: novelty mostly 32-36 Energy at seeds 4-5; common-deal value scoring made both arms worse (refuted)
  - #47: 9 edit-head/value combinations (screen, combine, agree): 8 of 9 below novelty alone (refuted)
  - #48, #52, #53: Count features added to pilot-v2; coevo-1 value search + novelty 0.03 still 28-35 basic Energy (r11-s0: 31; r21-s0: 31+2 DCE), one Chansey/Scyther type (leans refuted (count cause not isolated))
  - #54, #56, #57: League per-agent value climbs with two-stage adoption: 0-7 Trainers, 29-36 Energy (m1.v4 34/24/2, e0.0.v4 36/23/1) (refuted)
  - #59-#63: softmax(value/0.03) + re-test tournament: 29.0 Pokemon / 5.3 Trainers / 24.1 basic Energy, 0 of 8 archetypes at 50%; 225 of 277 swap ids Pokemon (refuted (swap-operator confound))
  - #64: Value search retired for simplicity (Occam) (retired, not a test)
- **Do not repeat:**
  - An edit head trained by regression on value-scored swaps, alone or in screen, combine or agree modes (#43, #47)
  - Common-deal (deterministic) value scoring as a fix (#46)
  - Closed-loop value PSRO with per-iteration pilot fine-tuning (#40); the same loop with softmax T=0.03 (#41)
  - Value search plus a novelty bonus of 0.03 as the cure for the Energy attractor (#43, #46), including inside co-evolution over the full pool (#52/#53)
  - Per-agent value climbs with two-stage real-game adoption (league, #54-#57) or with a softmax(value/0.03) plus re-test tournament (#59-#63)
  - The start-of-game value as an input to a matchup model (#37) or a deck-strength model (#38)
  - Recalibrating the value by training the pilot only on varied random decks (#42 flat 2-point spread; #43 same attractor when searched)
- **Untested variants:**
  - Rerun #36's Energy/Trainer ladder (value vs real) under pilot-v2 with count features and under the current walls-era population pilot. *Distinct:* Checks whether the count-encoding fix removes the reversal and whether the current REINFORCE draft head's encoder reading carries the same opening-state bias; never ran (#48; trainer_restore_test later deleted). *Cost:* low
  - The in-play value at game turn 5 as the scorer instead of the opening value. *Distinct:* Reads the deck after it has been played; #38 gave it +0.43 where the start value was -0.19; only ever one input inside the strength model (#39). *Cost:* medium
  - Two stages: value search for breadth, then a strength model choosing among many finalists and their Energy/Trainer block-swap variants (#39 Next). *Distinct:* The cheap proxy only proposes and an honest scorer decides; no run found. *Cost:* medium
  - [outside research] Conservative or ensemble lower-confidence-bound acceptance of value-proposed decks (offline model-based optimization, trust-region surrogate search). *Distinct:* Pessimism about the surrogate's out-of-distribution error, not about game noise (#56); conflicts with the Occam rule, so worth it only if a surrogate objective returns. *Cost:* deep research

### H68 · N13, N5 · inconclusive (weak) · Optimising the proxy harder finds better decks

- **Mechanism:** Search pressure on a proxy that misranks Energy against Trainers exploits its errors (Goodhart, winner's curse), though under a co-adapted pilot the same pressure can still raise measured strength.
- **Verdict:** Pushing the miscalibrated start-of-game value harder (edit head #43/#47, common deals #46, million-candidate matchup model #34) did not give better real decks and moved decks toward Energy floods. In #41, the one direct greedy vs T=0.03 contrast, greedy was stronger under all three pilots (60.7/71.9/60.2% vs 32.9/41.5/43.1%); every arm used 1-3 seeds and was judged under the optimised pilot or result #1's pilot, so whether more search pressure hurts in general is unsettled.
- **Tests:**
  - #41: Greedy beat T=0.03 vs archived field 60.7/71.9/60.2% vs 32.9/41.5/43.1%; head to head 72.5/75.8/59.4%; T=0.03 proposals 19.2-25.8 Energy; one seed each (supports prediction on strength, not human-likeness)
  - #43: Head 47.3/30.1 vs base 55.3/38.7; both 50.5/30.5 vs novelty 70.2/45.7; head arm throughput halved (29,310 vs 57,310); one seed; proposal-count bug (refuted (confounded))
  - #46: Common deals, seed 3: base 56.2 -> 43.2, novelty 71.8 -> 50.6 (scratch pilot); 40.5 -> 31.8, 43.3 -> 35.9 (result #1's pilot) (inconclusive (removes noise regulariser))
  - #47: Head modes mean 50.8/51.7/53.0 vs novelty alone 61.3 (seed-lucky s3 70.9), 8 of 9 below; plain base ~52.9 in #46 (weakened (head cancels novelty's gain))
  - #34: Matchup model, 8.6M candidates, predicted 0.75-0.90, real 26.5%; value 643k candidates 50.3%; real games 1,404 candidates 37.9% (supports overoptimisation (proxies differ))
  - #36: Value search Energy 17.4 -> 30.4; value 0.560/0.518/0.477/0.502 vs real 0.499/0.576/0.632/0.681 (supports proxy miscalibration)
  - #37: Matchup models fitted on search-generated data rank Trainer variants wrong; shape models exactly backwards (supports (feedback loop))
  - #39: Strength model error 0.046 avoids the Energy flood but ~2 s a candidate explores too little (low-pressure honest-proxy end)
  - #40: Closed greedy loop 60.7% vs archived field under original pilot, ~30 Energy (supports prediction on strength)
  - #56: Best of 4 noisy finalists beat current deck by ~2 points with none better; stage-1 vs re-test gaps up to 25 points (winner's curse)
  - #133-#134, #138, #140: Gate (--candidates 1 --select-z 1.0) top-12 distance 9.5 vs 15.7 ungated --candidates 3; largest type 15-26 vs 33-74; C/S decks 73 vs 79 of 99 (lower pressure helps shape, not type)
- **Do not repeat:**
  - --search-temperature 0.03 vs greedy as a single-seed comparison (#41)
  - --builder model with million-candidate search and no trust region (#34)
  - --edit-head as the main proposal source with greedy value acceptance, in any --head-mode (#43, #47)
  - --common-deals with the current value scorer (#46)
  - League adoption on 16 games against one opponent with no re-test (#56)
- **Untested variants:**
  - Overoptimisation curve: real win rate against search pressure (search seconds, climb budget, temperature or candidate count) over more than two points. *Distinct:* Measures the shape of the proxy-gap curve (Gao et al.-style) rather than one contrast; partial points (#34, #41, #138/#140) are confounded or measure shape only. *Cost:* low for the value builder; medium in the current loop
  - Replicated seeds of #41's greedy vs stochastic loop with a temperature sweep. *Distinct:* #41's 'two more seeds' never ran; needed before any status here is reliable. *Cost:* low-medium
  - Pessimistic or trust-region acceptance for the value-search builder (#43 and #46 Next). *Distinct:* Never built; #56 and --select-z are only the league and metagame analogues. *Cost:* medium
  - Pooled lower-confidence-bound or beat-the-incumbent's-best-of-last-5 acceptance in the current REINFORCE + --select loop. *Distinct:* Addresses noisy best-of-candidates selection pressure, open in the current loop. *Cost:* medium
  - [outside research] Reward-model overoptimisation scaling and conservative offline optimisation (COMs, trust-region model-based design). *Distinct:* The proxy's reversed rankings (#36) cannot be fixed by more search or acceptance tuning alone. *Cost:* deep research
- **New hypotheses (section 6):** H101

### H69 · N13 · inconclusive (weak) · Learned surrogate scorers rank decks

- **Mechanism:** A model fitted to search-generated, Energy-heavy decks labelled by one biased pilot cannot rank the Energy/Trainer contrast, and a wide search exploits it.
- **Verdict:** In the PSRO era (one seed, one fixed pilot, code deleted at #64/#65), the matchup ensemble used as the sole ranker of a million-candidate search on fewer than 50 decks was exploited (#34), and every cheap ranker misranked the Trainer variants (#36, #37). The accurate strength model needed ~480 games per deck and the archived lists in its fit (#38, a Rule 1 violation). Untested: surrogates refit without human lists, with trust regions or active Energy-vs-Trainer data, or used as a critic or pre-screen in the current REINFORCE loop.
- **Tests:**
  - #27: Design: matchup-model ranker (mean card embeddings + start value, 5-model ensemble, mean + beta x spread); real games decide entry; ~20x cheaper per step (design only)
  - #34: Model builder own-estimate error 0.587 (predicted 0.75-0.90 for decks winning 0-61%) vs games 0.081, value 0.268; fitted on 16-48 decks; one seed (underpowered (exploited))
  - #36: Start value predicted 0.560/0.518/0.477/0.502 vs real 0.499/0.576/0.632/0.681; search flooded Energy 17.4 -> 30.4 (refuted (value as ranker))
  - #37: Card-embedding model held-out MAE 0.157, winner 77.5%, Spearman +0.73 from ~95 decks; Trainer variants: value -0.20, shape -1.00, value+shape -1.00, embed -0.40 (mixed (training-data confound))
  - #38: Strength model MAE 0.058, rank +0.89; ~480 games per deck; archived lists in fit; level ~0.12 low (0.385-0.590 vs 0.525-0.700) (supported only as near-direct measurement)
  - #39: Error 0.046, ~2 s a candidate, 1,740 candidates; rank 0.00 on Trainer variants at 16 games; mixture lost 90.2% to value's deck (mixed)
  - #34, #56, #59/#60: Surrogate shortlist then real games (top 8 finalists; >=96 games then re-test, 2-point margin); ~±12 points noise at 16 games, gaps up to 25 (shortlist tried; picks least bad of bad shortlist)
  - #40, #41: Value calibration vs real games: mean |value - real| 0.038-0.191 greedy, 0.034-0.142 stochastic (tracked, no fix)
  - #64: One-copy change worth ~1-2 points; ~1,000 samples to resolve a 3-point effect (bounds surrogate resolution)
- **Do not repeat:**
  - Matchup ensemble (mean + 1.0 x spread, 5 members) as the ranker for an unconstrained million-candidate restart search on a model fitted to fewer than 50 decks (#34)
  - Deck-shape linear features (Energy/Trainer/Basic counts) as a ranker: weights basic Energy +0.14, Trainers -0.14, Trainer variants ranked exactly backwards (#37)
  - Deck-strength model with game statistics from 16 games per candidate as the sole in-search scorer with a fixed 120 s budget (#39)
  - Any surrogate fitted with the archived human lists as training rows (Rule 1; #38/#39)
  - Pilot start-of-game value as the deck ranker without recalibration (#34, #36)
  - Surrogate-ranked shortlist of top finalists confirmed by real games over an unconstrained search (#34, #56, #59/#60)
- **Untested variants:**
  - Two-stage search (#39 Next): value search or draft head for breadth, strength model (refit without archived lists) re-ranks many finalists plus Energy-for-Trainer block-swap variants, games decide. *Distinct:* Honest scorer over deliberate Energy/Trainer contrasts; no run found. *Cost:* medium
  - #34's trust-region surrogate (candidates within ~15 cards of measured decks) with two more seeds. *Distinct:* Targets the exploitation failure rather than accuracy. *Cost:* medium
  - #37's active-data fix: add controlled Energy-vs-Trainer block-swap variants of self-discovered shells to the surrogate's training data before refitting. *Distinct:* Attacks the data confound identified as the cause of the misranking. *Cost:* medium
  - #36's recalibration of the pilot value head on varied (built + random) decks, used as a scorer. *Distinct:* Recalibrates the existing surrogate rather than adding a new one. *Cost:* low-medium
  - Learned payoff or strength predictor as a baseline/critic for the REINFORCE draft head, or to pre-screen its 6-card draws before the 2,000-game judging. *Distinct:* Lowers draft-reward variance rather than replacing games; must respect Rule 3. *Cost:* medium
  - [outside research] Surrogate-assisted evolutionary optimization (model management, infill/acquisition criteria, trust-region BO such as TuRBO, active learning). *Distinct:* Absent from the first review; needed before any revival to avoid repeating #34's exploitation. *Cost:* deep research
- **New hypotheses (section 6):** H101, H107

## 6. New hypotheses from this session (H70-H113)

There is one entry per surviving candidate. Every entry has status untested. Each entry gives its rivals, design,
predictions and kill rule in brief, with all of its reviewers' required changes already applied (the reviews of C01-C12 and
C14 by three dedicated reviewers, the rest by one combined reviewer; all in `notes/data/cycle1/candidates.json`). Where a review only constrains how a result may be
read, that constraint is written into the entry. "Plan" refers to the first-cycle plan: a portfolio item (section 7) or
parked with its reason. The full designs are in `notes/data/cycle1/candidates.json`.

| H | C | Kind | Nodes | Hypothesis | Plan |
|---|---|---|---|---|---|
| H70 | C01 | infrastructure | N1, N12 | Round rule as an engine option, extended trace, ending-label fix | parked |
| H71 | C02 | outside research | N1, N12 | The 2000 specification: round length, turns, stall decks, procedure | item 8 |
| H72 | C03 | infrastructure | N4, N2, N12 | GPU-served searched probe with common random numbers | item 11 |
| H73 | C04 | infrastructure | N12, N5, N6, N7 | Recipe registry; bare vs stacked gate recipe | parked |
| H74 | C05 | diagnostic | N12 | Kill-horizon calibration on the logs | parked |
| H75 | C06 | diagnostic | N1 | Fidelity audit of the human side | parked |
| H76 | C07 | diagnostic | N4, N10, N3, N11, N9 | Zero-training judge zoo | item 2 |
| H77 | C08 | diagnostic | N11, N2, N4 | Attached-Energy count bug: sensitivity, then a fix | item 10 |
| H78 | C09 | diagnostic | N11, N1 | Open decklists and the stall plan | item 1 |
| H79 | C10 | diagnostic | N2, N12, N4 | Human-field tempo ladder and competence panel | item 12 |
| H80 | C11 | diagnostic | N2, N10, N12 | Prompt decisions hide the Trainer deficit | parked |
| H81 | C12 | diagnostic | N10, N4 | The search judge's leaf value | parked |
| H82 | C13 | diagnostic | N1, N2, N4, N12 | Ground truth on the representative field under the exact STS rule | item 3 |
| H83 | C14 | diagnostic | N1, N10, N5 | Draw-seeking in Evan's turn-limit runs | item 7 |
| H84 | C15 | diagnostic | N1, N5, N6 | What the round rule would change in one live iteration | parked |
| H85 | C16 | diagnostic | N4, N1, N12, N7, N5 | Empirical-game audit and premise test | parked |
| H86 | C17 | diagnostic | N4, N10, N3, N8, N9 | Matched pilot-v2 fine-tunes: payoff × field | item 16 (conditional) |
| H87 | C18 | diagnostic | N4, N3, N7, N2 | Separate best-response pilot against frozen walls | parked |
| H88 | C19 | diagnostic | N4, N7, N9 | Core transplant into wide decks | parked |
| H89 | C20 | diagnostic | N4, N5, N1 | Acceptance audit of designed edits | parked |
| H90 | C21 | diagnostic | N4, N5 | Judge-variance audit | parked |
| H91 | C22 | diagnostic | N3, N11 | Plasticity of the old pilot | parked |
| H92 | C23 | diagnostic | N6, N9, N5 | Null-drift accounting of composition drift | parked |
| H93 | C24 | diagnostic | N6, N5 | Draft-head bench: null and planted rewards | item 9 |
| H94 | C25 | diagnostic | N6, N5, N4 | Frozen-head and null-reward forks | item 15 (conditional) |
| H95 | C26 | diagnostic | N5, N6 | True effects of the head's proposals (paired) | parked |
| H96 | C27 | diagnostic | N5, N7 | Population rules on measured matrices | parked |
| H97 | C28 | diagnostic | N6, N7, N5, N4 | Valley test along block-wise edit paths | item 14 |
| H98 | C29 | diagnostic | N12, N5 | Three-reseed A/A of the gate recipe at 479 | item 5 |
| H99 | C30 | intervention | N9, N8, N10 | Pilot-first warm-up W (prevention start) | item 6 |
| H100 | C31 | diagnostic | N5, N6, N7, N4, N8, N9, N1 | Is the human field a fixed point of the loop? | parked |
| H101 | C32 | infrastructure | N5, N6, N7 | Surrogate metagame testbed | parked |
| H102 | C33 | decision for Evan | N1, N4, N12 | The game's specification: round rule, T, information sets, commits | item 4 |
| H103 | C34 | intervention | N1, N2, N4, N10 | Training-side test of the round rule | parked (needs Evan) |
| H104 | C35 | intervention | N10, N2 | Prize margin as the pilot's terminal reward | item 13 |
| H105 | C36 | intervention | N2, N10 | Branch starts from the pilot's own games | parked |
| H106 | C37 | intervention | N2, N10 | Expert iteration v4 | parked |
| H107 | C38 | intervention | N4, N5, N7 | In-loop powered judge screen | parked |
| H108 | C39 | intervention | N4, N8 | Reset-and-fine-tune judge | parked |
| H109 | C40 | decision for Evan | N9, N6, N12 | Stage 3 bootstrap components | item 4 |
| H110 | C41 | intervention | N9, N6, N8 | Proposal base measure from scratch: a factorial | parked |
| H111 | C42 | intervention | N6 | Best-of-K credit for the draft head | parked |
| H112 | C43 | intervention | N7, N6 | Wall-free island in Evan's 3-head league | parked |
| H113 | C44 | intervention | N7, N5 | Hard selection-time type cap on a wall-aware descriptor | parked |

### H70 · N1, N12 · untested · The event's round rule as an engine option, an extended per-turn trace and the ending-label fix

- **C id:** C01, infrastructure. **Plan:** parked. Build it (2-3 h) on the day C15, C16's rule cells, C31-B, C34 or
  C33(a') is scheduled, or when Evan answers D1.
- **Already measured, not new work:** the exact-vs-proxy question is settled by the exact STS chain (section 2, results not
  yet logged). The old rivals R1 (proxy-faithful), R2 (late lead) and R3 (early lead) are decided for R2. The validation
  replay is not rerun or extended to g8-15.
- **Design:**
  - **Trace:** add only the new per-turn fields (cards left in deck, attack available, attacked, Trainers played) to the
    existing `prizeTrace`. Move them into `env/runner.js` only if training or metagame code needs them, and then opt-in,
    so about 2,000 population games an iteration do not pay the IPC cost.
  - **Ending label:** take the reason from the engine's actual loss trigger (a draw-step deck-out vs no Pokémon after a
    KO), keeping the old label as `ending_legacy`. Reward paths (`runner.js:76`, `remote_worker.js:412` deckoutWin) stay on
    the legacy label, or the switch is logged as a reward change for `--deckout-win != 1`. Pre-state, then report, how
    many of the probe's 148 + 27 deck-out labels and 23 + 42 no-Pokémon labels change.
  - **`--round-rule T`,** off by default, through `env/game.js`, `env/runner.js`, `env/remote_worker.js` (games, tsearch and
    training commands) and `rl/metagame.py`. When game turn T+1 begins, more Prizes taken is a time-win and equal Prizes a
    time-tie. With the rule on, the 5,000-decision cap is decided the same way, and search clones crossing T are scored
    by the Prize decision, not as winner 0.
  - **Points:** one scheme everywhere. A deck scores 1 / 2/3 / 1/3 / 0 (the report's 3 / 2 / 1 / 0); the pilot gets
    per-seat points +1 / +1/3 / -1/3 / -1. A time-tie is not zero-sum, so `judged()`, the selection bars and every 0.5-draw
    assumption must state how they take it.
- **Checks (the kill rule):**
  - scripted states at turn T with Prizes 2-1 and 1-1;
  - 20 seeded rule-off games match the untimed engine move for move (trace hash);
  - with the rule off, 576/576 replays match the stored rows;
  - with the rule on at T in {30, 40, 50}, every game on `sts_greedy_all24`'s deals equals the offline prizeTrace scoring
    of the same game.

  Zero mismatches are allowed: any divergence is a bug, fixed before anything is evaluated.
- **H01 guard:** log time-win, time-tie and capped-game rates under the rule, and run `trace_loop.js --greedy` on a sample
  of capped and time-tie games, because a time-tie (-1/3) pays the pilot more than a loss.
- **Reading to pre-register:** SEs are clustered by wall-list pair (72 clusters of 8 games). Under the greedy judge the
  rule cuts the walls' share but leaves it above 0.5 at T 30-60 (0.54-0.67); it falls below 0.5 only near T 20.
  H103 must therefore state its predictions at the chosen T, with and without a search judge, on deck Energy counts or
  distance to the lists, not on the walls-vs-lists share.
- **Distinct from:** H01 (left the cap paying 0, better than a loss), H03 and H04 (only a plain draw was ever built, #140;
  #139/#147 re-scored stored rows), H02 (the label bug in #139's Next). The never-built factor is an unfinished game
  decided by Prizes, in the engine and at the decision cap, plus the label fix. The exact count at the cut is no longer new.
- **Cost:** about 2-3 h of code and tests; validation takes minutes on stored rows; no slot.
- **Evan:** building it needs no approval. Switching it on in any training or judged game is his decision (H102, D1); he
  asked only for a plain draw (#140).

### H71 · N1, N12 · untested · Outside research on the specification: round length, engine turns, human pace, stall decks, procedure rules

- **C id:** C02, outside research. **Plan:** item 8 (agent lane, about 5 agent-hours, no machine).
- **Rivals:**
  - R-fast: 20-50 engine turns a round, time called often, few deck-outs, so the prior on T is at most 50.
  - R-slow: 60-70+ engine turns a round, or time rarely reached; stall decks were weak for other reasons.
  - R-unknown: fewer than 2 independent sources, so H82's whole T curve stands.

  H-pilot-slow is a separate axis, not a rival: human Haymaker and Wigglytuff Prize wins in 12-20 engine turns, against
  our pilots' 34-41.
- **Design:**
  - **Before reading anything:** write down the formula T = (round seconds - setup and shuffle overhead) / (seconds per
    engine turn) as a range, with its overhead allowances and the rule for combining sources. Write down how the T
    interval maps onto H82, H100 and H103, never revised after results.
  - **Seed from the repo:** Q1, Q4 and Q5 start from what the repo already holds (#139's STS page quote,
    `notes/sts-2000-engine-check.md`, the MTR citations in `research_notes/degenerate-env.md`). The time box goes to the
    unknowns.
  - **Order and budget:**
    - Q1 (round length per age division, procedure at time, points 3/2/1/0, one game per Swiss round, rounds and top cut)
      and Q2 (engine turns per 20-minute round, share of rounds reaching time, and a human deck-out rate to set against
      JF2's 27-35%) come first, with at least 2 h.
    - Q4 (the 2000 procedure rules) comes next.
    - Q3 (stall decks) runs only after T is recorded. It counts only records from time-called rounds; "they were rare" is
      non-discriminating. Q3 never sets T, the rule's form or adoption.
    - Q5-Q7 get leftover time: the Worlds 2005 and MTR rules, fixed before any run; the age divisions; archives, for
      identification only.
  - **Units and evidence quality:** one unit, engine turns (both players' turns), with each source's division recorded.
    2000 in-person sources outrank online and modern retro recordings, which are anchors with a stated pace adjustment.
  - **H-pilot-slow, matched:** human turns to six Prizes for a named matchup against our pilot's engine turns for the same
    pair of lists. Prize wins only, median and range, noting the selection bias toward quick wins.
  - **Q1 readout:** names the time-call procedure. The engine's maxTurns scores every unfinished game as a draw, so a Prize
    tiebreak needs H70.
  - **Method:** the deep-research workflow (needs a subagent tool), and every quote re-checked by a second agent.
- **Predictions:**
  - R-fast: 10-25 turns per player a round, reports of time being called, rare deck-outs; T prior at most 50.
  - R-slow: 60-70+ engine turns, or time rarely binding; T prior 70+.
  - R-unknown: fewer than 2 independent sources for Q2.
- **Kill rule:** a 4 h box plus 1 h of quote checking. A question with no primary source after 45 min is logged as
  "unknown", with what was searched. Outside data on which decks won never sets a parameter.
- **Distinct from:** H03's and H61's outside-research variants (never run); #144 covered only RL literature. Log the
  outcome as tried rows of H03 and H61, and in `notes/evan-requests.md` rows 24 and 33.
- **Evan:** no contact with players and no live evaluation without him; human game data stays evaluation-only.

### H72 · N4, N2, N12 · untested · GPU-served searched probe with common random numbers (CRN): is the in-loop search the judge #147 measured, and how much of what search changes is re-deal noise?

- **C id:** C03, infrastructure. **Plan:** item 11 (tier B, about 8 dh). It uses the GPU only while at most 2 screens are
  live; otherwise it counts as a slot.
- **Rivals:** Same-judge vs Different-judge (the GPU path's step cap, top-k ties or numerics differ); Re-deal noise vs
  CRN-null.
- **Design:**
  - **Plumbing and code:** `notes/scripts/probe_searched.py`. A `judgeSearch` pass-through, per-job search flags and
    `searchStats` in `rl/gpu_matrix.py`. A CRN flag in `PolicySearchAgent`: one seed per determinization, drawn outside
    the options loop (`env/agents.js:377-380`). The tsearch CRN is a separate edit in `remote_worker.js`'s line loop, with
    its own tests.
  - **Tests (`env/tools/test_search.js`):** k 1 replays greedy exactly; under CRN, identical options score identically.
  - **Primary parity test, at the decision level:** at least 500 positions, the same master seed, k4 d4 independent.
    CPU-ONNX `PolicySearchAgent` (`walls_vs_humans.js`, `resetcap499.onnx`) against the GPU `RemotePilot`, comparing
    action agreement and value correlation on lines from identical clones. Baselines: a CPU-vs-CPU same-seed rerun
    (expect 1.0) and a GPU-vs-GPU same-seed rerun.
  - **Arm (a), a gross check only:** matches #147 exactly (maxTurns 0, maxSteps 40, horizon 1, both seats; seeds
    SEED·1000003 + p·STRIDE + g, seed 11, stride 32). It is flagged if more than 0.15 from 0.573, because #147's CI is
    [0.469, 0.677] and the comparison is unpaired.
  - **CRN manipulation check:** per determinization, the correlation of line scores across the k options (clearly
    positive, above the independent case), and the share of lines whose RNG stream stays aligned past the first action.
  - **Positions:** 2,000 human-free population positions, the only gate for any training-side use of CRN, and 500
    human-vs-human positions, as diagnostics. Each configuration runs twice with independent master seeds: k4 d4
    independent, k4 d4 CRN, k8 d2 CRN and k16 d1. Configurations are compared at matched realised lines, over one
    denominator (decisions with at least 3 legal options among the top k), with SEs clustered by game.
- **Predictions:**
  - Same-judge: CPU-GPU agreement within 2 SE of GPU-GPU, and equal capped and line-error rates.
  - Different-judge: more than 2 SE below, or differing rates.
  - Re-deal noise: independent self-agreement at most 0.65, CRN at least 0.80, and the off-top rate down at least 25%
    (about 0.5 to at most 0.38).
  - CRN-null: independent agreement already at least 0.80, and CRN changes the off-top rate by less than 10%.
  - In between (0.65-0.80, or a 10-25% drop): partial re-deal noise, so H106 proceeds only at CRN of at least 0.80.
- **Kill rule:**
  - Different-judge: debug before any searched result is used, `scr-jsearch479`'s included.
  - Independent agreement of at least 0.85: keep the current search.
  - Drop CRN if it raises agreement by less than 0.05 and moves the changed share by less than 0.05.
  - Drop k8 d2 if its line errors exceed 1%.
- **Distinct from:** H22's do-not-repeat CPU k4 d4 runs (rerun here only as validation); H05 and H11 (independent re-deals
  were never named as a cause); H23 (the in-loop GPU path was never validated).
- **Cost:**
  - 6-8 h of code;
  - 20-40 min for the 3 arms (2-4 s a game untimed), or 1-2 h for a 576-deal extension;
  - about 320k lines for the positions, about 10 min.

### H73 · N12, N5, N6, N7 · untested · A named recipe registry, then a bare-versus-stacked delta-debug of the gate recipe

- **C id:** C04, infrastructure. **Plan:** parked. This cycle the registry is written by hand. Launcher enforcement (4-6 h)
  can wait. Revisit if H98 shows the gate is real.
- **Rivals:** H-inert-stack (floor 3, group 0.3, practice 250, type cap 0.5 with turnover every 5, wide turnover and
  protect 20 do nothing at the gate's 479 state) vs H-load-bearing.
- **Design:**
  - **Registry:** `notes/recipes.json` or `rl/recipes.py`, holding fully resolved named recipes, each flag with its
    value, source entry and status. 'adopted-bare' is lab.json main_args with nothing added: turnover every 10 at 0.15,
    not wide, with `--swaps 6` and `--shaping 0.1` kept.
  - **Launcher:** `screen.py --recipe NAME` rejects duplicate flags (gate479 passed `--turnover-every` twice). It writes
    the resolved flags, diff, hypothesis, rivals, bands and kill rule. `rl.metagame` warns on pre-adoption argparse
    defaults. Before launch it prints the fully resolved diff between gate-bare and gate479, including `screen.py`'s
    inherited pre-#127 main_args: only the seven stacked flags may differ; any other difference is listed and matched.
  - **gate-bare:** adopted-bare + `--select --candidates 1 --select-z 1`, from `scr-resetcap/population_it0479.pt` with
    `--seed 1 --reseed 2 --keep 5` (snapshots at 484/489/494/499), 20 iterations. It runs beside a concurrent current-code
    replicate of gate479 on a new reseed, which serves as the gated A/A; a second gate-bare seed if slots allow. Dropping
    `--draft-h-in-floor` changes the inherited head's draws at once.
- **Predictions and decision:** the primary readout is the window-mean distance over 490-499; the co-primary is wall-core
  decks at 499.
  - Inert: |difference| at most the gated A/A difference (floor 2 × 2.6 cards).
  - Load-bearing: more than twice that.
  - In between: one more seed.

  Moves, acc-prop and type are secondary. Pilot-node readouts for the practice and varied-field levers: the final-pilot
  walls verdict (band from #137) and competence on a fixed panel (bar 0.06). Run 30 iterations unless 20 is justified for
  pilot generality.
- **Kill rule:** the wall-core threshold comes from the concurrent gated replicate, checked at 489. Stop before 499 only on
  a gap of more than twice the calibrated noise for 3 consecutive iterations.
- **Binding follow-ups:**
  - **Bisection, if load-bearing:** {practice, cap + every 5} vs {floor, group, wide + protect}, with the floor in its own
    branch or a one-factor follow-up (H32's verifier); 2 runs, about 3.5 slot-hours.
  - **Scope of a null:** it licenses only "inert for keeping the 479 gated state over 20 iterations". Pruning the Stage 3
    recipe needs a fresh-start bare-vs-stack pair at 40 or more iterations, run regardless. The 2^(4-1) fresh-start
    factorial (8 arms, 30-40+ slot-hours) is its own proposal. A null within about 1.5 times the ungated band is weak.
- **Distinct from:** H25 (only stacked gate variants were run); H32 (the floor ablation was killed at 453); H16 and H40
  (practice and turnover were never isolated under the gate). H40's do-not-repeat bars an unseparated joint removal
  (`scr-draft`), hence the binding bisection.
- **Cost:** 5-6 h of code (about 4 h if the ledger-family lookup is deferred). gate-bare takes about 5.3 min an iteration,
  1.7-1.9 slot-hours. The verdict tooling from H76 is counted, or that readout is dropped.

### H74 · N12 · untested · Kill-horizon calibration: do early readings predict final ones, node by node?

- **C id:** C05, diagnostic. **Plan:** parked for the first periodic review (`notes/method.md` section 15).
- **Rivals:** H-short-horizon, H-early-informative, H-node-specific.
- **Design:** offline on `runs/screens/*/log.jsonl`, the snapshots and the lab logs.
  - **Primary statistic:** reliability at each horizon, (Var_arms - Var_AA) / Var_arms, per metric. The A/A pairs are
    ctl479 vs resetcap, lab 001/002, and the near-A/A pairs.
  - **Verdict agreement:** three-way (worse beyond A/A, within noise, better beyond A/A), using distance above about 5 or
    twice the A/A RMS, type above 50 and the competence bar 0.06. It is reported separately for pairs whose final is a
    real effect and pairs whose final is null.
  - **Controls:** positive controls with a predicted earliest horizon (gate479 type 23 vs 74; lamv479 distance +3.7/+9.5;
    turns40 Energy -3.5 and steps -56). The negative control is the A/A pair.
  - **Windows and resolution:** windows do not overlap (early readings up to h; the final is the last 3 iterations).
    Per-iteration log metrics serve +1/+3/+5/+10. Type and wall-core are read only at snapshots: +5/+10/+15 for 479
    forks, +20 for ctl, gate, gatevs and league479, +9/+19/+29/+39 for 460 forks. Relapse constants are bracketed to
    5-10-iteration bins.
  - **Pairs:** 15 in all (seven share ctl479, three share reset), with a cluster bootstrap or leave-one-control-out by
    fork group. turns40 and anchor (which end at +13) and vs479 and lamv479 (+16) are labelled truncated.
  - **Lab:** only the cards with at least 2 rungs (vq4-b, aux, deckcross-w, hist4, ent02-b, slotbind-w, lr2; n = 7),
    against the lab's A/A swings (Elo σ 8.8, swings of about 40). Failed-early cards are censored.
  - **Range:** the analysis calibrates horizons only up to about 20 iterations; 30-40 only through reset, resetcap,
    resetent and gamma.
- **Predictions:**
  - H-node-specific: moves and held-back counts readable from +1-3; distance needs at least 1.5 relapse times (relapse is
    10-16 iterations from 479); pilot Elo unreliable at one segment.
  - H-short-horizon: early differences beyond A/A that fail to predict the final ones.
  - H-early-informative: early beyond-A/A signs that match the final ones.

  Thresholds are set to what the effective n can resolve.
- **Kill rule:** analysis only.
- **Distinct from:** H62 (truncated-curve ranking untested); methodology idea 8.
- **Cost:** 2.5-3.5 h of CPU-only agent time.

### H75 · N1 · untested · Adversarial fidelity audit of the human side, with a paired re-probe per fix

- **C id:** C06, diagnostic. **Plan:** parked (low prior; its fixes are submodule edits awaiting Evan, plan section 4 item
  4).
- **Rivals:**
  - F1 faithful.
  - F2 a fault slows or weakens the lists.
  - F3, added: a fix matters, but a pilot trained on the old engine cannot use it.
- **Design:**
  - **Fix-and-re-probe arm, run even if the audit finds nothing:** #139's verified deviations (2003 Confusion,
    simultaneous-win draw, Maintenance order, Thick Skinned cure after a blocked Power, the empty-deck ending label) go
    straight to flagged fixes and paired re-probes. They are not re-audited.
  - **Narrow audit:** only what neither `notes/scripts/ryuu_sts_cards_tests.js` nor `ryuu_rulings_tests.js` covers. Those
    suites' Ditto D1-D21, Mewtwo M1-M15, Rainbow X1/X3, Jigglypuff X6 and #1's T-series are passing baselines. In scope:
    - the 2000 setup and turn procedure: first-turn draw, turn-1 attack and Trainer legality, the mulligan extra-card
      option and its count, Basic placement and reveal order;
    - the high-frequency human cards no suite covers: Scyther, Hitmonchan, Electabuzz, Magmar, Nightly Garbage Run, the
      Do the Wave bench count, Ditto copying Thick Skinned and Chansey's Scrunch and Double-edge, and any main text of
      Item Finder, Lass, Scoop Up and Sneak Attack left unexercised.
  - **Each fix:** a ryuu-play edit, a dist rebuild and a runtime flag, default off, through `env/engine.js`, `game.js`,
    `runner.js` and `remote_worker.js`. A seeded-2000 trace-hash check with flags off runs before any live screen's
    workers restart.
  - **Re-probe:** the `scr-resetcap` 499 walls, greedy, `walls_vs_humans.js` on #137's deals, 1,152 games, against #139's
    0.702.
    - Rules that fire in nearly every game get 2-4 deal seeds (2,304-4,608 games), so that 0.03 is at least 2.5 SE.
    - Each fix reports its firing fraction and the decisions it changed.
    - One combined re-probe runs with all confirmed fixes on.
    - F3 test: for a fix firing in at least 10% of games, or with |Δ| of at least 0.02, a 10-20-iteration fine-tune on the
      fixed engine, then a re-probe.
- **Predictions:**
  - F1: only cosmetic or out-of-field deviations, and every re-probe |Δ| below 0.02.
  - F2: at least one fix moves the walls at least 0.03 toward the lists (Holm across fixes, or replicated on a fresh
    seed), with the lists' median Prize-win turn down at least 1. The test is two-sided. A result of 0.02-0.03 is
    inconclusive and is replicated.
  - Combined shift: if it is at least 0.10, or the walls fall below 0.60 greedy, H82, H85 and H103 are re-read under the
    fixed engine.
- **Kill rule:** stop when every in-scope item is verified or refuted. Skip the re-probe for a deviation that never fires in
  200 traced human-vs-wall games.
- **Distinct from:** H02 (refuted only for the walls' cards; its untested "fix the minor deviations and rerun" is the
  first arm). #1's 68-test Ditto and promo suite is cited, not repeated.
- **Cost:** half a day for the audit, plus 1-2 h per fix and about 10 min per re-probe.
- **Evan:** submodule commits only with his go-ahead (H102, D7).

### H76 · N4, N10, N3, N11, N9 · untested · Zero-training judge zoo: wall-naive and matched pilots on the walls' verdict

- **C id:** C07, diagnostic. **Plan:** item 2 (a GPU probe beside at most 2 screens, about 2.5 dh).
- **Rivals:**
  - H-payoff: deck-out wins paid 1 make any competent pilot rate the walls high.
  - H-exposure: co-adaptation with the walls does it.
  - the familiarity confound;
  - H-human-side (H19);
  - H-count-bug;
  - H-open-decklists;
  - H-architecture (A1);
  - H-weak;
  - null.
- **Design:** no training. `probe_matchups.py` runs over checkpoints that load strict-clean under the current token
  bounds; any failure goes to ONNX and `walls_vs_humans.js` on #139's 576 deals. The 3 walls of `scr-resetcap` 499 play
  the 24 lists, greedy, with the judge on both seats, on #137/#147's deals.
  - **Arm (a):** the `runs/abl` from-scratch deck-out-1 pilots, 16 games a pair: base and base-s2 at it19/39/59/79;
    base-cont, ent-cont and explore-cont; explore10 and its -s2; and the it39 slot-bind, no-deck, deck-cross, cand-self,
    ability-text, deck-inter, deck-cross-sb and gae1 pilots.
  - **Arm (b):** the human-field lineage: a4-tok it249, #33's deckout-w1/w0, and pilot-scratch it249. Pairings: X/X;
    a4-tok on the lists with resetcap499 on the walls; and the reverse. A human-free twin plays the walls against
    `runs/probe/wide12.json`, a fixed seeded full-pool draw written before anything is read.
  - **Primary contrasts, pre-registered and Holm-corrected:**
    - deckout-w1 vs w0 at 64-96 games a pair, with the it4/it9/it14 dose-response and a bootstrap paired SE (effect of at
      least 3 paired SE);
    - the seat swap;
    - a4-tok X/X;
    - slot-bind, no-deck and deck-cross vs base, each replicated at it19 and it39.
  - **Seed band:** all 8 seed pairs (base/base-s2, explore10/-s2 at it19/39/59/79). The architecture margin is
    max(0.05, 2√2·σ_seed).
  - **Covariates for every checkpoint:** skill (SimpleBot on the archived lists); speed (median turn of the lists' Prize
    wins); exposure (share of training games against Snorlax JU or Potion Energy decks). Trends are within-lineage or
    from a mixed model; there are no pooled Spearman cut-offs.
  - **Bookkeeping:** games of 40 turns or fewer are scored beside the full score. `probe_matchups.py` gets a per-game dump
    (i, j, seat, winner, ending, turns). #139's label is corrected after play. Cap and error rates are reported per judge.
- **Predictions:**
  - Payoff: w1 - w0 of at least 3 paired SE (about 0.08), with w1 at least 0.55 and at least 50% deck-out wins. A high
    verdict counts for payoff only if it persists in games of 40 turns or fewer, or after conditioning on speed.
  - Exposure: every wall-naive pilot at most 0.40, and w1 - w0 within ±0.05.
  - Familiarity: the a4-tok family at most 0.35-0.40 while abl pilots are at least 0.55.
  - H19: walls 499 with lists played by a4-tok at most 0.55 opens the lever; at least 0.65 closes it.
  - Count bug, no-deck, encoder: a shift of at least the margin at both it19 and it39.
- **Kill rule:**
  - Probe base-cont it39, ent-cont it39 and base-s2 it79 first. If none clears the seed band or 0.55, stop the abl skill
    trace. The architecture pairs and arm (b) always run.
  - Drop a judge with more than 2% errors or caps.
  - Do not read a pair whose pilots differ by more than 0.1 against SimpleBot.
  - H86 runs only if (b) lands in exposure, familiarity or 0.40-0.55.
- **Labelling:** pilot-scratch replicates pilot-v2's deck-out-0 condition; it is not independent payoff evidence. A w1 - w0
  within ±0.05 leaves H52's matched from-scratch deck-out 0/1 judge pair open.
- **Distinct from:** H18 and H22 (sweeps of population pilots are do-not-repeat); H19, H20, H52, H57, H58; anomaly A1.
- **Cost:** about 47k greedy games: 1.5-2 h of wall time beside the screens (RL_GPU_SHARE 0.15, 4 workers), plus 1.5 h of
  scripting.

### H77 · N11, N2, N4 · untested · The live attached-Energy count bug: zero-training sensitivity, then an isolated fix

- **C id:** C08, diagnostic. **Plan:** item 10, step 1 (about 5 dh); steps 2-3 in cycle 2, under R1 or R3.
- **Rivals:**
  - R1 distorts: Bench and opposing slots are misread, which hurts the typed-cost human attackers while the walls pay
    colorless costs.
  - R2 inert: the 256-way aux embedding learned each (slot, copies) code.
  - R3 opposite channel: the walls read opposing Energy through the bug to aim Energy Removal, so a fix helps the walls.
- **Step 1, forward passes only:** pilots `scr-resetcap` 499 and pilot-v2, on human-vs-human, population and
  walls-vs-list states.
  - **(i) Probes:** linear or MLP probes on per-token or per-slot hidden states, decoding typed Energy copies per slot and
    whether each slot's attacks can be paid. Results by slot class (own Active, own Bench, opposing Active, opposing Bench)
    and by aux-code frequency.
  - **(ii) Mean-ablation:** of the ENERGY tokens' `count_features`/`count_proj` input only, with the aux embedding kept
    (a separate arm if it is ablated). The control is a HAND-count channel of matched variance. Flips and |dV| by decision
    class.
  - **(iii) Metamorphic Bench swaps in token space:** SLOT positions 1-12 move with their feature rows, along with the slot
    index in UNDER/TOOL/ENERGY aux; the +1-Energy edit changes both the ENERGY token's copies and `slots[o+10]`. Each
    swap's |dV| is normalised by the state's own +1-typed-Energy |dV|, and a positional baseline swaps two Pokémon with
    identical attachments.
  - **Primary comparison, matched:** a fixed student against bug seeds 1 and 2, all distilled from the same teacher in
    minutes. `031-pilot-slotbind-w` is a ratio control only.
- **Predictions (step 1):**
  - R1: probe accuracy drops on the Bench, on opposing slots and on rare codes; at least 3% flips on Energy decisions;
    normalised Energy-swap |dV| of at least 0.5 against a positional baseline of at most 0.2; effects concentrated on the
    own Bench, attach and retreat.
  - R2: flat accuracy, under 1% flips, ratios at most 1.3.
  - R3: effects concentrated on opposing ENERGY tokens and on ER and SER target choices.
- **Step 2, only under R1 or R3:**
  - **The fix:** ENERGY count features computed from copies (aux - 8·slot). There are no owner or slot embeddings and no
    same-slot bias; it is not `--slot-bind`. The flag is threaded through the TokenPointerNet config, `train.py` config
    keys, `gpu_matrix`, `crossplay` and the ONNX and puzzle export, with a `rl/tests.py` check that the Bench ENERGY count
    equals copies.
  - **Students:** at least 2 fix and 2 bug students (`rl/warmstart.py`, 400+ games, 2+ epochs), trained on the human-free
    testbed (about half a day to build unless H78 or H104 builds it; `train.py --init-from` expects `ckpt['model']`).
  - **Power:** paired games with shared deals and swapped seats, so that a 0.03 verdict difference and a 3-point deck-out
    difference are each at least 2.5 SE.
  - **Adoption:** only on human-free non-inferiority (Elo against both bug students beyond their gap, and puzzles).
    Human-vs-human tempo and the walls' verdict stay diagnostic.
- **Step 3, a fork pair:** from population_it0479, fixed vs unfixed, both distilled the same way. At least 2 reseeds per arm,
  or an A/A fork pair. Kill at 10 iterations only on the probe (a verdict difference below 0.03). Shape and Chansey+Snorlax
  are read at 20, against the A/A spread (up to 14 mid-trajectory).
- **Kill rule:** stop after step 1 under R2.
- **Distinct from:** H58 (slot binding cold and warm, judged on Elo and competence only; do-not-repeat); H60 (single-fork
  shape readings).
- **Cost:** step 1 takes 4-6 h of agent time and minutes of GPU. Step 2 takes 2-3 h of code, the half-day testbed and
  about 3 h of distillation.

### H78 · N11, N1 · untested · Open decklists: does seeing the opponent's whole list power the walls' stall plan?

- **C id:** C09, diagnostic. **Plan:** item 1 (about 1 dh).
- **Rivals:**
  - R1 information leak;
  - R2 irrelevant;
  - R3 out of distribution;
  - R4 symmetric use (both seat effects above 0.03 and equal).

  A reverse asymmetry is also mapped to a conclusion.
- **Design:**
  - **Per-seat hide, model-side:** a `TokenPointerNet.encode` option masks only OPP_DECKLIST (kind 10) tokens and keeps
    MY_UNSEEN. The arms run through `probe_matchups.py`'s per-deck `--pilot`/`--pilot-b` slots, which follow the deck
    across seat swaps. A `rl/tests.py` check confirms that outputs ignore kind-10 changes and still respond to MY_UNSEEN.
  - **Five arms on #147's protocol:** 3 walls of `scr-resetcap` 499 × 24 lists × 16, identical deals, greedy, 1,152 games
    an arm.
    - shown: reuse `runs/probe/judge/resetcap499.json`, rerun once as a determinism check;
    - hidden from the walls;
    - hidden from the lists;
    - hidden from both;
    - decoy: a wrong, in-distribution human list given to each seat.

    No turn limit in the primary arms (T = 60 optional). Each arm logs its deck-out share and game lengths, and a check
    confirms that deals and coin flips stay paired after play diverges.
  - **Human-vs-human pace panel:** with a shown-lists baseline on the same deals.
  - **Estimands, pre-registered:** asymmetry A = 2·S_shown - S_wallsHidden - S_listsHidden, in the walls' score. The
    interaction comes from the both-hidden arm and is reported apart. Power comes from the measured discordance and a
    cluster bootstrap over the 24 lists (walls reported separately): about 60-75% for 0.05, so 0.06 is the detectable
    effect.
- **Predictions:**
  - R1: A of at least 0.05, and the decoy hurts the walls as much as hiding, or more. An asymmetry alone does not confirm
    R1.
  - R2: both seat effects at most 0.03, with 90% upper bounds below 0.05.
  - R3: each single-seat mask costs its own seat more than 0.10, while the decoy costs about 0.
  - R4: both effects above 0.03 and equal.
- **Kill rule:** close as R2 only if the upper 90% bounds of A and of the walls' own-seat effect are both below 0.05. A
  result in 0.03-0.05 gets one more deal seed.
- **Step 2, cycle 2, under R1 or R3:** a list-blind copy and a control fine-tuned 10 iterations, 2 seeds per arm, on the
  H77/H104 testbed (not a 499 fork). Both copies are checked against the 0.06 competence bar; stop if the list-blind copy
  loses more than 0.06, since a skill loss biases the walls' verdict upward, against R1.
- **Caveat:** the count bug (S32) is present in every arm.
- **Distinct from:** H57 (the no-deck screen #73-74 hid both lists from scratch and was judged against SimpleBot); H76's
  no-deck pair is its pre-read.
- **Cost:** step 1 takes about 30 min of code and 10 min of GPU (1,152 games take 98 s). Step 2 takes two 10-iteration
  processes, about 1 h in 2 slots.
- **Evan:** hiding opponents' lists in training is an information-set change for him (H102, D6).

### H79 · N2, N12, N4 · untested · Human-field tempo ladder and a powered competence panel

- **C id:** C10, diagnostic. **Plan:** item 12 (tier B; stage 1 about 4 dh, stage 2 about 5.5 dh).
- **Rivals:**
  - R1 in-turn tactics.
  - R2 beyond the turn, split by an endings readout into objective-driven stalling vs horizon limits.
  - R3 deck-resource myopia.

  The count bug is a named confound for R2.
- **Stage 1, no searched path needed:**
  - **Instrumentation:** per-seat Prizes at game turn 20 in the runner and remote rows (the valueAtTurn hook); a per-game
    dump; Trainer plays by card class; explicit mirror pairs; endings and turns kept in `env/tools/matrix.js` for the
    SimpleBot rung.
  - **Rungs:** SimpleBot, pilot-v2, `scr-resetcap` 499 and `scr-ctl479` 499, all greedy. Each plays 1,024 games on fixed
    seeds: 8 lists, one per archetype, 64 ordered pairs × 16. These are replays with per-game turn and Prize logging; the
    JF2 files hold only ending counts.
  - **The decision table:** written down before anything is read.
- **Stage 2:**
  - **Searched rung:** `scr-resetcap` 499 with one-turn k4 d4 on both seats, on H72's path or on CPU overnight with about
    4 workers. A CRN k8 d2 rung only if H72 shows that CRN matters.
  - **Puzzles:** regenerated from 4,000 seeded heuristic games (time one 400-game part first, `--max` above 300): about 970
    Trainer-first, 160 PlusPower-only and a prompt-led class (Gust, ER).
  - **Line-scored mode:** fixed coins, with heads and tails both required. Opponent decisions inside the turn are scored
    adversarially. Draw Trainers that are UNPROVABLE are masked or reported apart. An oracle self-check requires the
    generator's own winning line to score 100%. Determinizations never read the true deck order.
  - **Error bars:** class SEs by cluster bootstrap over source games, after removing near-duplicate positions.
  - **Count-bug controls:** a slot-bind rung if a comparable checkpoint exists; otherwise R2 carries the count-bug caveat,
    and each rung reports turns to its first fully powered attacker.
  - **Export:** an ONNX export of ctl479 499 for the puzzle rungs.
- **Primary contrast:** searched minus greedy on resetcap 499 in the tempo-vs-tempo stratum (Haymaker, Hitmonchan/Magmar,
  Rain Dance, Electabuzz/Mr. Mime, Wigglytuff; about 400 games, SE about 2.4 points), paired by ordered pair × seed, with
  a bootstrap SE.
  - **Pace metrics:** unconditional: Prizes by turns 10/20/30, and the restricted mean time to the 6th Prize with
    deck-outs and draws censored. The median Prize-win turn conditions on the outcome and is not decisive.
  - **Decision table:** pace change (below 0.2 / 0.2-0.5 / at least 0.5) × deck-out change (down at least 5 / within ±5 /
    up at least 5) maps to R1, R2, R3 or inconclusive.
  - **Reading R2:** a flat result counts as R2 only if the searched rung shows its instrumentation working (its
    decision-change rate and the puzzle positive control).
  - **Endings readout:** deck-out winners behind on Prizes, and passes while an attack was legal, point to the objective.
    Even Prizes with slow Energy build-up point to the horizon.
  - **Fork noise:** the ctl479-resetcap gap is descriptive only.
- **Predictions:**
  - R1: pace up at least 0.5 Prizes by turn 20, and deck-outs down at least 5 points (from about 35%).
  - R2: pace up less than 0.2 and deck-outs within ±5, with search shown working.
  - R3: pace up at least 0.5, deck-outs flat or up, and more draw-Trainer plays.
- **Kill rule:** the searched rung stops at 512 games if deck-outs are within ±3 points and pace within ±0.2 (R2), but only
  if the instrumentation check passes.
- **Use of the panel:** its scores rank pilots between runs and never feed an in-run selection.
- **Distinct from:** H05 and H22 (search was used only in walls-vs-list games); H06 and H65 (re-scoring the 408 first-move
  puzzles is do-not-repeat); JF2 (greedy only, S35).
- **Cost:** 7-9 h of code and checks, plus 2-4 CPU-hours.

### H80 · N2, N10, N12 · untested · Prompt decisions: is the Trainer devaluation decided inside the Trainer's prompt?

- **C id:** C11, diagnostic. **Plan:** parked (needs H79's line-scored puzzles and exact prompt scoring, a day or more).
- **Rivals:**
  - R1 prompt incompetence;
  - R2 main-phase timing;
  - R3 credit fades in long games;
  - R4, added: the count bug. It predicts a gap concentrated where the right answer depends on the opponent's attached
    Energy (ER, SER, many Gust targets), varying with the target's slot and shrinking under slot binding.
- **Code facts:** qprobe and tsearch skip open prompts (`env/remote_worker.js:276, 355`); psearch plays prompts greedily;
  `Game.clone` throws on an open prompt, so prompts are probed from the state before the Trainer.
- **Design:**
  - **(1) Census:** the share of decisions that are prompts. It sets the expected plays per game and n per group, and is a
    feasibility gate only.
  - **(2) Exact prompt scoring on win-this-turn puzzles:** force the winning Trainer, and label each answer winning or
    losing by exhaustive search over the rest of the turn. (Alternatively, match prompt-free puzzles on decisions
    remaining in the turn.)
  - **(3) Prompt Q-probe:**
    - **Runner change:** `job.first` extended to an array of keys, with a "not on offer" check at each step and a unit
      check that each probed card's prompt is reached.
    - **What is probed per card:** for Computer Search and Item Finder, hold or enumerate the discard pair and enumerate
      the fetch; for ER and SER, the target Pokémon, then the Energy; for Gust, the bench target. Cancel is excluded or
      reported apart. Multi-step prompts are probed at every step, conditioned on the earlier answers.
    - **Deck fetches:** run with own-side redeal off, or drop any probe with a "not on offer" line.
    - **Lines:** up to 8 answers × 16 re-dealt lines to the end of the game; greedy lines first, sampled lines only if the
      greedy gap passes 0.3.
    - **Sample size:** at least about 1,000 probes per card, or pre-registered pooled groups (targets: Gust, ER, SER;
      search: CS, IF) with stated n.
    - **Pilots:** `scr-resetcap` 499 and pilot-v2 (one pilot first if the budget is short), and a slot-bind pilot if one
      exists. The gap is stratified by target slot and by whether the right answer depends on Energy.
  - **(4) Trainer panel, only if R1's contrast passes:** `trainer_value.py` (8 lists × 4 groups × 64, identical deals)
    under greedy play, prompt-only lookahead and main-only psearch.
  - **R3 sub-readout:** credit share by decisions-to-end bin for the walls-era pilot on walls-vs-list games, against
    #75/#77's A4-era bins, with n per bin.
- **Predictions:** the paired contrast is the prompt gap minus the main-phase gap, in the same games, matched on option
  count.
  - R1: the contrast is at least +0.5, with a CI excluding 0.
  - R2: the contrast is at most 0, or its upper bound is below 0.5.
  - R3: the 80+ bin falls below the A4-era bin by more than its CI.

  Q-best agreement is used only with a split-half noise ceiling, after collapsing interchangeable answers; otherwise it
  is dropped.
- **Kill rule:** steps 1-2 gate feasibility only (enough prompt decisions with at least 2 non-equivalent answers to reach
  n). Step 3 stops after 500 probes if the contrast's upper bound is below 0.5.
- **Distinct from:** H08 (prompt and setup decisions untested); H06 and H07; #79-80 (main phase only, do-not-repeat); #92's
  greedy panel.
- **Cost:** about half a day of code, plus 4-6 h of probe runs at reduced concurrency beside the screens.

### H81 · N10, N4 · untested · A leaf value for the policy that plays judged games: is the searched judge's remaining wall preference the critic's sampled-play bias?

- **C id:** C12, diagnostic. **Plan:** parked (needs H72's searched path and a per-decision logger, 3-4 h; cycle 2 if H82's
  stage 2 or H79 leaves a searched plateau).
- **Rivals:**
  - R1 leaf bias: the critic is fitted to sampled play;
  - R2 not the leaf;
  - R3, added: a cluster-specific feature bias, the count bug.
- **Design:** the critic and pilot are `scr-resetcap` 499; the walls are its #829, #796 and #809. The human-free decks and
  the Trainer-rich cluster come from a named population snapshot.
  - **Step 1, the sibling-leaf statistic (not cluster-mean calibration):**
    - **Positions:** at sampled root decisions (Trainer vs non-Trainer; wall side vs list side), the critic scores k
      candidate end-of-turn leaves. Each leaf gets its re-dealt Monte Carlo outcome under greedy, sampled and searched
      continuations.
    - **Statistic:** the slope (or rank correlation) of value differences on outcome differences, and the mean signed
      error on Trainer-minus-alternative pairs. Both are reported per policy and cluster, split by attached Energy count
      and slot index.
    - **Power:** SEs clustered by game; 3-5k games per policy and cluster for the greedy and sampled continuations.
    - **Reuse:** `runs/probe/wvh_psearch_both_g0-7.jsonl` serves its 192 deals; only the other 384 are played.
    - **Target choice:** greedy-target V_eval is used only if the greedy- and searched-continuation errors agree within
      about 0.02; otherwise its targets come from searched games.
  - **Step 2:** V_eval and a matched control V_samp: the same MLP, frozen trunk, decks, 20k games, sampling and training,
    but with sampled-continuation targets. Three leaf arms (critic, V_samp, V_eval) play the same 576 deals.
    - A critic-leaf A/A (two search seeds) measures noise and correlation. If the SE exceeds 0.022, add deals or
      determinizations.
    - Held-out Brier is reported separately on walls, Trainer-rich and human-list games, on new deals.
    - H79's searched rung, with critic leaves and its own A/A, is the deck-out baseline.
- **Predictions:**
  - R1: V_eval - V_samp in the walls' searched score is at most -0.04, with a 95% CI excluding 0.
  - R2: the 90% CI lies within ±0.04.
  - Otherwise inconclusive.

  A frozen-trunk null does not clear the leaf while the trunk reads the corrupted count.
- **Kill rule:** stop after step 1 if the sibling statistic shows no gap specific to a policy or cluster. Stop step 2 if
  V_eval's held-out Brier gain is below 5% on the human-list and Trainer-rich clusters.
- **Distinct from:** H47 (refit on sampled self-play); H50, H48 and H21; H22's untested "leaf value not from the population
  pilot".
- **Cost:**
  - 3-4 h of engineering;
  - on CPU, searched runs take about 3.7 h (step 1) and 7 h (step 2). Alternatively, 1-2 h to build a GPU fixed-deal
    driver, then 60-90 min of runs;
  - GPU memory stays under 13 GB;
  - 20k greedy games take 40-60 min on GPU.

### H82 · N1, N2, N4, N12 · tested, stage 1 (#156, #159) · Condition-matched ground truth on the representative field: three wall sets against all 24 lists under the exact STS rule over a turn grid, across a strength ladder

- **Result, stage 1 (#156, grade A on its registered bands):** E+P + (J2 over all 24 at T 50-60: 0.492 [90% 0.455,
  0.531]; T50 55.9 [49.3, 63.6]); P - (J2 clockless 0.607 [0.568, 0.645], 72% of the walls' wins by deck-out);
  Plateau - (W(J2, Π) 0.393); Imbalance + (walls-only gain -0.016 [-0.049, +0.016] against the lists' 0.169); E holds
  for A (W(J1, Π) 0.542) and misses for blind B (0.563) and C (0.635); ExP's J1 clause holds only for C, which has no J2
  cell, so ExP stays open there. Under greedy play the Energy-heavy set C (main 460) is the strongest of the three
  (plain 0.774, T50 13.1). Do not repeat: J1 on sets A (games 0-15), B or C, or J2 / walls-only on set A, on seed 11 /
  stride 32 deals; the open cells are J2 on B and C (about 2.3 CPU-h each), J3 and level 2.
- **Result, stage 1b (#159):** J2 on set C over all 24: E+P fails on C (W(T 50-60) 0.562 [0.529, 0.596]); ExP holds on
  C (W(J2, Π) 0.447, by 0.003); Plateau - (0.447); P - (clockless 0.618 [0.585, 0.651]); T50 44.6 [37.2, 49.7]. Paired
  J2 − J1 on C −0.156 [−0.193, −0.118]. The verdict on both searched sets is now set by T alone (both lose for T 20-45,
  both win at 60), so C02's round length decides it. Do not repeat: J2 on set C on seed 11 / stride 32 deals.
- **C id:** C13, diagnostic. **Plan:** item 3 (stage 1, a CPU probe, about 3 dh). J2 on set B, J3 and level 2 wait for H72
  (item 11).
- **Rivals:**
  - E: the missing clock is first-order;
  - ExP: the clock matters only with search;
  - P: play strength alone flips the clockless verdict;
  - Plateau/W;
  - Imbalance: search helps only the tempo side.

  The subset-artifact rival is dropped; its prior is the greedy subset gap of at most 0.03.
- **New fact behind it:** every searched probe used one list per archetype, and the Wigglytuff stand-in (Lieu) is an
  outlier. Greedy walls score 0.396 against Lieu but 0.706 against the 10 Wigglytuff lists (range 0.396-1.000).
- **Already decided on set A (re-registered against the exact results in section 2):** J1's exact W(T) at T 20-45 is
  0.48-0.58 (mean about 0.53). That decides ExP's J1 clause and P's 0.04 clause on set A. The subset's both-seat W(T) at
  T 20-45 is 0.33-0.44, against 0.648 untimed. Search reruns vary: 0.573 vs 0.648 on identical deals.
- **Design:**
  - **Wall sets:** A = `scr-resetcap` 499 (#829/#796/#809), B = `scr-gate479` 499, C = main `seg_0460`. Each is the 3
    best decks by the population's own judged score.
  - **Field and deals:** all 24 lists, seats alternated, identical seeded deals. "Field-weighted" means equal weight per
    list over all 24; the archetype-weighted subset numbers are dropped.
  - **Reuse:** `sts_greedy_all24`, `sts_search_human_sub` and `sts_search_both_sub` are reused. Only new games are played
    (g8-15 for A, 16 a pair), and the 26 games missing from `sts_search_both_sub` are finished first, which takes minutes.
  - **Stage 1, CPU, no new code (`walls_vs_humans.js`, 4 workers):**
    - greedy exact-rule curves for sets B and C (576 games each);
    - walls-only k4 d4 on A's 576 deals (psearch on the walls, greedy lists);
    - J2 both-seat k4 d4 on A's remaining 384 all-24 deals, about 2.5 CPU-hours. This is the replication of the linchpin
      row (E+P, 192 games, about ±0.10) that `notes/method.md` section 4 requires.
  - **Stage 2, gated on H72 being built and validated** (CPU fallback about 25-35 h): J2 on set B; J3 (CRN k8); level 2
    nested within-turn search (new code in `PolicySearchAgent`, 2-4 h); the invasion readout (a traced resident 24 × 24).
  - **Scoring:** every game untimed, with plain draws, and under the exact STS rule at T in G = {20, 25, 30, 35, 40, 45,
    50, 60, 70, 80}.
  - **Summary statistic:** Π = uniform over 20-45, replaced by H71's interval only if that arrives before results are
    opened. The whole curve is always reported.
  - **Primary readout, assumption-free:** the break-even turn T50 at which W(J, T) crosses 0.5, per judge and wall set,
    with a pair-clustered bootstrap. It is compared with H71's interval later; Π never decides the verdict.
  - **Roles:** sets B and C are the blind confirmatory cells for E vs ExP. The clockless strength ladder (J2 on all 24, J3,
    level 2) and the walls-only seat are the primary open tests, each with a stated minimum detectable effect.
- **Predictions (B and C blind):**
  - E: W(J1, Π) at most 0.55.
  - ExP: W(J1, Π) at least 0.58, with W(J2, Π) at most 0.45.
  - P: J2 clockless on all 24 below 0.50 (subset prior 0.648).
  - E+P replicates: J2 at T 50-60 at most 0.50, with a 90% CI below 0.55.
  - Plateau: W(J2, Π) at least 0.52.
  - Imbalance: walls-only gain at most 0.02, against a human-side gain of at least 0.10.
- **Kill rule, interval-based futility:**
  - A strength rung stops only when the upper 90% bound of its paired gain over the rung below is below 0.05, with at
    least 192 paired games. SEs come from the observed rerun spread (0.573 vs 0.648) unless H72's CRN is validated.
  - J2 on all 24 stops after 192 new games if clockless is below 0.48.
  - The walls-only cell stops after 192 games if the upper 90% bound of its gain is below 0.05.
- **Distinct from:** H03, H05, H22 and H23 (subset deals, proxy count, plain draws; nothing is replayed except to add new
  games); H18 (J1 is one pilot, not another sweep).
- **Cost:**
  - stage 1: about 1.5 h of agent time and about 6 CPU-hours (B and C greedy plus walls-only take 2.5-3.5 h);
  - code lines for nested search, a traced pilot-v2 path, a traced resident 24 × 24, and wall-set extraction for B and C;
  - the GPU-served probe counts as a screen slot, or runs only with at most 2 screens.

### H83 · N1, N10, N5 · untested · Draw-seeking in Evan's turn-limit runs: a pilot learning the draw, selection of draw-prone decks, or shared drift?

- **C id:** C14, diagnostic. **Plan:** item 7 (a GPU job counted as 1 slot, about 2.5 dh).
- **Evan:** completes the analysis of his own turn-limit idea (requests 24-25).
- **Rivals:**
  - D0 shared drift;
  - D1 pilot draw-seeking;
  - D2 deck draw-seeking.

  D3 (cycles and caps) is a separate diagnostic of the cap and of anomaly A6, reported apart.
- **Design:**
  - **(a) Deck × pilot replays:** under each run's own limit, in sampled play. Random pairs of population decks come from
    `population_it*.pt`, with one fixed pair list (shared pair_keys) in every cell, 2,000 games a cell.
    - Limit 40: decks {`scr-turns40` 0489, `scr-ctl479` 0489} × their pilots, plus an anchor cell, `scr-ctl479`'s starting
      479 snapshot (the shared decks and pilot).
    - Limit 70: at 489, where `scr-turns70` peaked at about 25% time endings (or at both 489 and 494). Its fall from 25% to
      12% over 489-496 is a pre-stated observation: D1 predicts it stays high, while D0 and D2 allow the fall.
    - The 60-turn pair runs last or is dropped (confounded by greedy judging and the gate).
  - **Components, measured from the anchor:** shared drift = control-by-control minus anchor; deck effect = mean deck
    contrast; pilot effect = mean pilot contrast; and their interaction.
  - **Calibration:** each run's own cell must reproduce its logged limit-ending share (about 93% at 40) within 5 points,
    since training used search_p 0.1.
  - **Behaviour logging, inside the replays:** per game, the Prize difference at the limit and who was behind. Per side
    and turn, whether an attack was available and taken, and draw-Trainer plays, binned by Prize state and turns left
    (1-3, 4-8, 9+ game turns).
  - **(c) Cap diagnostic:** option keys are logged for games ending capped in sampled play inside (a). `scr-jsearch479`'s
    truncated search lines are dropped: they are rollouts cut at 40 steps, not capped games.
- **Predictions:**
  - D1: a pilot effect of at least 10 points at limit 40, with a behind-minus-ahead attack and draw-Trainer gap of at
    least 0.10 near the limit. A pilot effect with a behind-minus-ahead gap below 0.05 counts as competence loss, not
    draw-seeking.
  - D2: a deck effect of at least 15 points, tracking the decks' Pokémon count.
  - D0: both effects below 5 points.

  A component counts if it is at least 1/3 of the anchor-to-own rise and above 3 SE (pair-clustered bootstrap).
- **Kill rule:** stop if the own-by-own cell misses its logged limit share by more than 5 points, or if no cell gives at
  least half of (own minus anchor). The cap trace stops at 50 capped games if no sequence repeats 3 or more times.
- **Distinct from:** H04 (refuted plain-draw limits without decomposing the rise in limit endings); H01 (its untested trace
  of capped games; its do-not-repeat requires logging the time share by the losing side); anomaly A6.
- **Cost:** about 1 h of code (`max_turns` in `GpuMatrix.play`, a `--max-turns` flag, the driver) and 45-60 min of GPU.
  A per-decision recorder, if H70 has not built one, takes 2-4 h.

### H84 · N1, N5, N6 · untested · Would the round rule change what the loop selects? Re-score one live iteration's judged games (human-free)

- **C id:** C15, diagnostic. **Plan:** parked. It needs H70's runner trace, a per-game dump and an offline replica of
  pick/rloo (about 5-7 h), and its answer does not gate H103.
- **Rivals:**
  - SI inert.
  - SR toward the human shape: Trainer coefficient above 0 and Energy at most 0.
  - SW toward Energy-heavy aggro: Energy or basic-Pokémon coefficient above 0 and Trainer at most 0.

  These are signed contrasts, with Pokémon as the reference, so SR and SW cannot both pass.
- **Design:**
  - **Launch:** from `runs/screens/scr-gate479/config.json` and `scr-ctl479/config.json`, with `--freeze-pilot --reseed S
    --iters 491`.
  - **Dump:** every judged game is saved: game, sides, seat, candidate index, result, turns and trace (H70's trace passed
    through `env/remote_worker.js row()`), plus the candidates' decks and ev fields.
  - **Offline replica:** of `pick()`, the tally, rloo and batch-SD scaling. The reproduction check matches the new run's own
    select row (moved, held_back, acc, prop) and per-deck sums exactly.
  - **Scoring rules:**
    - untimed;
    - the exact STS rule at T in H82's grid, from per-turn Prizes at T (not #139's end-of-game proxy);
    - plain draws at T: a positive control against H04's in-loop nulls. SI at T 60-70 is expected, and it is no new
      evidence on plain draws. This arm can run now from the existing 'turns' field.
  - **Noise null, matched to the perturbation:** redraw only the games lasting past T, count-matched per candidate, at the
    candidate's untimed rate, 20 times (as `null_searched` does).
  - **Primary readout, paired at the move level:** for every proposal, accepted or not, (candidate minus parent) of
    Δ(rule minus untimed) is regressed on the move's ΔTrainers and ΔEnergy, with deck-clustered errors. The deck-level
    regression and the acc-row comparison are secondary.
  - **Primary T:** W over Π = turns 20-45, pooled, pre-registered; the full grid is secondary.
  - **Per-card advantage sums:** reported raw and after the batch-SD scaling that `draft.update` applies.
  - **Turnover:** iteration 490 has no turnover, so its bottom-15% choice is computed offline or turnover is left out of
    the claims.
  - **Sample:** about 198 entities an iteration under the gate (about 20 games each) and 396 under ctl (about 10 each). The
    two seeds re-judge the same decks; they are not independent units.
- **Predictions:**
  - SI: flips at Π inside the null's 95% band, and move-level slopes whose intervals span 0.
  - SR: flips above the band, with SR's signed pattern.
  - SW: flips above the band, with SW's signed pattern and its interval excluding 0.
- **Kill rule:** an untimed recomputation that does not reproduce the run's own decisions stops the work until the
  bookkeeping is fixed.
- **Reading:** fixed play rules out only the scoring channel of a clock. SW blocks H103's stage 2. SI does not block it, but
  makes stage 2 conditional on stage 1 showing CA, the pilot channel.
- **Distinct from:** H04 and H23 (limits inside training screens, read on shape); H29; H89 (designed variants, not the
  loop's own decisions).
- **Cost:** two one-iteration runs per seed (6-7 min each), about 2 h of analysis, 1-1.5 h for the dump and replica, and
  H70's 3-4 h unless that is built first.

### H85 · N4, N1, N12, N7, N5 · untested · Empirical-game audit and premise test: walls, self-discovered types, wide decks and the human field under a judge ladder

- **C id:** C16, diagnostic. **Plan:** parked. Stage 1 runs in cycle 2 after H76 names the judges; stage 2 needs H72. Hard
  dependencies, in order: H70, H72, H82's grid and Π (H76 for J5).
- **Rivals:**
  - R-judge-bound/PR4: under every affordable judge the walls are a resolved Condorcet winner or the only sink, and they
    invade the human field. This is scoped to the current pilot family, since the count bug is in every judge.
  - R-selection-bound;
  - R-discovery-bound/PR1;
  - PR2 clock alone;
  - PR3 strength alone.
- **Design:**
  - **Judges, defined before running (base checkpoint, search and its k and d, draw turn, rule scoring):**
    - J0: pilot-v2 greedy.
    - J1: resetcap499 greedy.
    - J1': J1 with plain draws at 50 and 60.
    - J2: one-turn CRN k4 d4 on both seats (H72), on a named base pilot.
    - J3: J2 with the cut.
    - J5: dropped unless H76 has run.

    The walls' edges run under both base pilots if affordable. No further population pilots join as greedy judges (H22's
    do-not-repeat).
  - **Reuse:** the on-disk J0/J1 human 24 × 24 matrices and the set-A-vs-lists matrices (#137 own/own and v2/v2) are
    replayed only to collect H70's per-turn trace. The searched walls × 24-list cells are shared with H82, which owns them
    (same deals, CRN seeds and wall sets).
  - **Panel:** built by its own script, k-means over card counts per checkpoint with a named selection score (not
    `screen_types.py`). Panel decks are evaluated only on deals not used to pick them.
  - **Stage 1, the cheaper spend:** greedy J0, J1 and J1', and exact STS re-scoring (needs H70), on a trimmed panel: 6
    walls, 6 non-wall types, 2 wide decks, 1-2 lists per archetype. About 1-2 h of GPU.
  - **Stage 2:** J2 with CRN on the walls × non-wall and core-list edges, gated on stage 1 not already deciding. J2 runs on
    the walls' edges unconditionally; no skip keys on J1 or J1'.
  - **Statistics:**
    - **Sequential testing:** anytime-valid confidence sequences (or alpha-spending), with Holm or a union bound over the
      9-wall × non-wall family. Any edge that supports R-selection-bound is replayed at a fixed n on fresh deals and must
      replicate.
    - **"Beats the walls":** defined against each wall and against their equal-weight mixture, with pooled statistics
      beside the edges (each non-wall pooled over the walls; the wall set's mean against the non-wall set). The minimum
      detectable effect is stated, or the decisive J3 edges are raised to about 150 games.
    - **Invasion of σ_H:** fixed, non-adaptive counts of at least 48 games on edges against lists holding more than 0.02
      of σ_H. σ_H's bootstrap uncertainty is propagated into one interval, with n_eff. σ_H is computed under the same
      judge as the fitness, or the cross-judge result is labelled secondary.
    - **PR3:** a paired-bootstrap interval on the TV change, or an "unchanged" threshold of 0.05.
  - **Decision of record:** the human-free submatrix, read both under the exact STS rule at Π and under J3's plain draws.
    The two must agree before selection-bound or discovery-bound is credited.
  - **Outcome table, written in advance:** it covers most J3 edges unresolved; walls losing to the human field without
    Condorcet status; the two base pilots disagreeing; J3 and the exact rule disagreeing. Each cell names its follow-up
    (H102, H107, exploration, H71 or H75).
- **Predictions:**
  - R-judge-bound: under J3 the walls beat every self-discovered and wide deck and at least 6 of 8 archetypes on resolved
    edges, with Nash mass on the walls of at least 0.9 and invasion fitness above 0.
  - R-selection-bound: at least one non-wall beats the walls under J3, replicated, with the walls' mass in the human-free
    submatrix below 0.5, while J1 wins every edge.
  - R-discovery-bound: the walls are Condorcet winners in the human-free submatrix while at least 2 archetypes beat them,
    and their invasion fitness at Π is below 0.
  - PR2: J1 at Π gives invasion fitness below 0, while untimed J1 gives more than +0.10.
  - PR3: untimed J2 already gives fitness below 0, and Π moves it by less than 0.05.
- **Distinct from:** H18 and H22 (re-probing resetcap499's walls under #147's pilots; sweeps of further population pilots);
  JF2 (S35); H96 (rules simulated on these matrices).
- **Cost:**
  - the full 49-deck panel: each greedy judge about 900 new pairs, 29-58k games, 40-75 min;
  - J2 on the walls' edges: about 360 edges, 14-17k searched games, 6-8 h of GPU;
  - with the searched 24 × 24 σ_H and the 150-game caps: 12-16 h searched, scheduled against the 3-screen budget;
  - code: copy `hodge_audit.py` into `notes/scripts/`, plus half a day to a day of extensions.

### H86 · N4, N10, N3, N8, N9 · untested · Delta-debug the judge's wall verdict: matched pilot-v2 fine-tunes crossing deck-out payoff with training field

- **C id:** C17, diagnostic. **Plan:** item 16, conditional: it runs only if H76's arm (b) lands in exposure, familiarity
  or 0.40-0.55. 3 slots, about 12 dh.
- **Rivals:**
  - H-payoff;
  - H-exposure;
  - H-familiarity (only partly equalised between the W and P arms);
  - H-interaction;
  - H-incumbency;
  - H-slow-accumulation;
  - wave 2: H-fast-learner vs H-reset-viable.
- **Design:**
  - **Fine-tunes:** `rl/train.py` fine-tunes of pilot-v2 it349 (`--d 256 --tok-layers 4 --heads 8 --count-features`),
    league off, seed 1, 40 iterations.
  - **Settings:** every PPO setting is written out (lr 2e-4, epochs 2, ent 0.01, gamma 1, lam 0.95, shaping 0; the
    `train.py` defaults are lr 3e-4 and epochs 3). `--workers` is set per arm (about 6) so three jobs stay within 80%.
  - **Ending label:** the fix is an opt-in flag (or is applied only with no screens live). pilot-v2's iteration-0 verdict
    and ending mix are re-measured under it and used as the baseline instead of 0.264.
  - **Wave 1:**
    - W1: 512 wide decks over the full pool, with a coverage floor of at least 8 decks per card and almost none holding
      both Chansey and Snorlax; 2,048 pairs; deck-out 1.
    - P1: `scr-resetcap` 479's 99 decks plus wide pairs at about 1 in 9, deck-out 1. This is a positive control, not a
      judge-sweep point.
    - P0: P1 at deck-out 0.
    - W0 runs whenever W1 rises by at least 0.10.
  - **Wave 2:**
    - H1: the 24 lists plus wide decks, quarantined.
    - bal-1: only if W1 ends at most 0.40 and P1 at least 0.55. It runs after checking that the Chansey/Snorlax walls fall
      in one cluster (k by silhouette, the wall cluster checked by card presence) and that at least 3 non-wall clusters
      with enough decks exist.
  - **Readouts at 0/5/10/20/30/40:** walls vs the 24 lists, 16 games a pair (1,152); the human-free twin; the walls'
    ending mix and deck-out share. At 40, the 2 × 2 seat pairing and a head-to-head against pilot-v2.
  - **Replicates:** seed 2 of P1 and P0 runs regardless.
- **Predictions:**
  - Payoff: W1 at least 0.50 (conditional on stall opportunity; W1's deck-out share is reported), P1 at least 0.55, P0 at
    most 0.35.
  - Exposure: P0 at least 0.50, W1 at most 0.35.
  - Familiarity: W0 and W1 at least 0.45, and P0 at least 0.45.
  - Slow accumulation: P1 at most 0.40 at 40.

  The decisive contrasts are P1 - P0 (payoff given exposure), W1 - W0 (payoff with no walls in the field) and P1 - W1,
  each a paired difference with a CI on identical deals. The bar is at least 2 pair-clustered SE (about 0.07), replacing
  the old 0.04 "not a cause" bar.
- **Kill rule:** each arm stops at 40, or earlier if its head-to-head on wide decks falls by more than 60 Elo or more than
  2% of games are capped. If P1 is below 0.45 at 40, extend P1 to 80.
- **Distinct from:** H18, H20 and H52 (whole-pilot comparisons, do-not-repeat); #33's w0/w1 pair (card ablations only);
  H43 and H16. H76 is its free stage-0 pre-read.
- **Cost:** 2.5 h of code plus 8-10 slot-hours: 7-9 arm-runs at 2-3 min an iteration with three in parallel, about two
  evenings. The fine-tunes occupy screen slots.
- **Evan:** whether a pilot-v2 descendant may become a method component is his call (plan section 4, item 6). Every
  checkpoint stays quarantined.

### H87 · N4, N3, N7, N2 · untested · A separate best-response pilot against frozen walls: can learnable counter-play beat them when their pilot cannot adapt?

- **C id:** C18, diagnostic. **Plan:** parked. It is subordinate to H76's payoff/exposure split and needs a held-out-pilot
  readout and 2 slots; cycle 2 if H76 points to exposure.
- **Rivals:**
  - R-exploitable: the gain must hold within 0.10 against an unseen walls pilot.
  - R-robust-clockless.
  - R-human-specific.
  - R-incompetent, added: H at most 0.40, with most losses by Prizes (not deck-out), and the learner's training win rate
    plateauing.
  - A new outcome: a gain that appears only against resetcap499 exploits a frozen pilot's quirks.

  Each rival states its predicted ending mix (#141's Prize-race finding).
- **Design:**
  - **Opponent:** `rl/train.py --opponent-pilot P`, with the frozen model built from its own checkpoint config through
    `rl/metagame.py`'s `frozen()` helper (not `build_model(args, info)`), and an assertion that both use the same token
    encoding. Only the learner's seat is recorded. The frozen resetcap499 pilot plays the 3 #137 walls plus 9 more of its
    best walls.
  - **Arms:** two arms from pilot-v2 it349, 30 iterations, with the adopted PPO settings and pilot-v2's architecture flags
    given explicitly (`--lr 2e-4 --epochs 2`, the intended shaping, matching `--d`/`--tok-layers`/`--deck-mode`,
    `--inference gpu`).
    - H: the 24 lists as challengers (diagnosis only).
    - S: 24 self-discovered non-wall decks and 24 wide decks.
  - **Readouts:** at 0/5/10/15 (and 30): the challengers against the 3 #137 walls and 3 held-out walls, greedy, 8 games a
    pair on #139's deals, with both pilots. The iteration-0 readout is taken under identical conditions.
  - **Held-out-pilot readout:** the walls piloted by a population pilot never trained against (`scr-resetent` 496 or the
    `scr-gate479` pilot, both of which rate the walls 0.68-0.75). Optionally, a re-adaptation check: fine-tune a copy of the
    walls' pilot 5 iterations against the final learner, then re-read.
  - **Per-archetype splits:** descriptive; no decision on an archetype with fewer than 7 lists.
- **Predictions (gains from each arm's own iteration-0 score):**
  - R-exploitable: H gains to at least 0.55 by 30, mostly through Prize wins before turn 45; held-out walls within 0.05;
    the unseen pilot within 0.10; S at least 0.45.
  - R-robust-clockless: H at most 0.40, with at least 50% of its losses by deck-out after turn 55.
  - R-human-specific: H at least 0.55 while S stays at most 0.35.

  A result in 0.40-0.55 has a pre-registered reading and a seed-2 rerun.
- **Kill rule:** gated on the per-iteration training win trend (about 600 games an iteration) plus the readouts. Stop at 15
  only if the readout gain is below 2 SE of a difference (about 0.07) and the training slope over 5-15 is within noise of
  0; otherwise run to 30. Stop if more than 2% of games are capped, and trace them.
- **Distinct from:** H17 (shared-network challenger practice; its untested separate best-response pilot); H19 (two-sided
  practice); H38 (separate networks in #55-57, before the walls).
- **Cost:** 3-4 h of code; about 2-3 min an iteration (1-1.5 h an arm) plus the readouts. Check `nvidia-smi` with two models
  in one process.

### H88 · N4, N7, N9 · untested · Core transplant: does a fresh wide field pull toward the walls' core under each pilot?

- **C id:** C19, diagnostic. **Plan:** parked. Its verdict needs W (H99); cycle 2, with the Haymaker-core control.
- **Rivals:**
  - H1 co-adapted gradient;
  - H2 stall is strong;
  - H-valley;
  - generic card quality, carried by the staples.
- **Design:**
  - **The core:** the 8-16 cards most over-represented in the resetcap-499 population relative to 99 wide decks. It is
    split into a wall-specific block (Chansey, Snorlax, healing special Energy) and a shared-staple block (Oak, Gambler,
    ER, DCE, Bill).
  - **Mandatory selection-matched control:** the Haymaker core (the over-represented cards of the 7 Haymaker lists,
    diagnosis only), kind-matched and of the same size.
  - **Variants:** in 99 wide decks (fixed seed), remove a kind-matched set, using line-aware kind-matched removal and
    insertion with copy-limit checks, then add one of:
    - FULL: the core;
    - HALF: the core's Pokémon plus CTRL's Trainer and Energy part;
    - CTRL: a kind-matched random package.
  - **Games:** 16 per variant against the wide field, on common deals (a sampled-pair mode with pair_keys). For the
    deciding pilots (499, base-cont, W), 32 games per host deck or more host decks, so that the H1/H2 gap is at least 3
    clustered SE. SEs are clustered by host deck (bootstrap over the 99), and the 0.04-0.08 band is assigned in advance.
  - **Pilots:** resetcap-499, pilot-v2, base-cont it39 (not wall-naive), W (required; the H1/H2 split stays provisional
    until W exists), and random init as the floor.
  - **Positive control:** the walls with their core replaced by CTRL, 3 walls × 99 wide opponents × 4 games per variant,
    on at least 2 wall sets (resetcap 499 and main 460), with its SE stated.
- **Predictions:**
  - H1: FULL - CTRL at least +0.12 under 499, and at most +0.04 under pilot-v2, base-cont and W.
  - H2: at least +0.08 under every competent plain-result pilot, carried by the wall-specific block.
  - Generic quality: the staples or the Haymaker core gain as much.
  - H-valley: FULL - CTRL at most +0.03 and HALF - CTRL about 0 under every pilot, while the positive control is at least
    +0.10.

  HALF - CTRL and the random-init floor get written predictions under H1 and H2.
- **Kill rule:** if the positive control moves the walls by less than 0.05 under 499, recompute the core once, else stop.
- **Distinct from:** H18 and H22 (whole walls against lists); H07 (swaps inside existing decks); #127's hand-made variants.
- **Cost:** 2.5-3 h of code and 1-2 h of GPU at RL_GPU_SHARE 0.15 with 4-6 workers beside 3 screens. Check first that
  base-cont it39 and pilot-v2 load under the current token bounds.

### H89 · N4, N5, N1 · untested · Acceptance audit: would a powered searched verdict, a clone-invariant panel or a Prize-decided cut reverse what selection accepts?

- **C id:** C20, diagnostic. **Plan:** parked. It needs H72's search and maxTurns pass-through and H95's aligned builder
  (about a day with them), and it gates H107; cycle 2.
- **Rivals:**
  - R-strength;
  - R-redundancy;
  - R-draw-haven;
  - R-invariant;
  - R-neutral, added: the drift comes from proposals, and the judge is nearly indifferent. As a free pre-check, report
    acc minus prop per kind over every gated screen's log.
- **Design:**
  - **Frozen state:** `scr-t60gate479`'s last checkpoint (80 of 99 decks hold both Chansey and Snorlax).
  - **Variants per deck:** the parent and in-place substitutions:
    - (t) Trainers +4, Pokémon -4;
    - (p) Pokémon +4, Trainers -4: the drift itself, as a positive control;
    - (h) taken from H95's paired head-draw games (merged, with ρ reported once).
  - **Builder fallbacks:** when the deck's Trainers are at the copy limit, a rule-generic choice (Trainers drawn uniformly
    from the pool's Trainer kind, logged). Never strand an evolution. Log each variant's realised dP/dT/dE.
  - **Panel:** at most 2 of its 8 decks are walls (stratified by the wall flag), and its wall share is reported.
  - **Opponents:**
    - U: 16 population decks, drawn as the loop draws them.
    - P: the clone-invariant panel, at 16 deals per deck so that the SE of P - U is at most 0.02.
  - **Judges, with the 60-turn limit:** G greedy; S CRN k4 d4 on both seats, paired with G on the same 8 searched U deals
    (a per-deal S - G with the measured ρ).
  - **Readings:** every game is read twice, with the plain draw at 0.5 and under the event's rule.
  - **Search hygiene:** capped search lines are logged per arm, and S is reported with and without games that had capped
    lines. One smoke game confirms that searched rows carry prizesLeft and ending.
- **Predictions (each states the SE it is read at):**
  - R-strength: Δ(t) under S minus G at least +0.05, and Δ(p) under S minus G at most -0.05.
  - R-redundancy: Δ(t) under P minus U at least +0.04 and Δ(p) under P minus U at most -0.04, with S about equal to G.
  - R-draw-haven: the share of games reaching the cut whose Prize reading favours the variant over the parent (the
    counterfactual is exact on those games). The maximum possible Δ shift is stated, given cut rates of about 28% under G
    and about 45% under S.
  - R-invariant: an equivalence test (TOST) at a reachable bound (SE at most 0.015, or ±0.05); "not separable" when the CIs
    straddle the bound.
- **Kill rule:** only the code-bug stop at ρ below 0.1. The R-invariant early stop on 30 decks is dropped.
- **Distinct from:** H07 (#68's swaps under greedy and SimpleBot); H23 (`scr-jsearch479`, inert); H24 and H25 (gate noise,
  not judge preference); H84 (the loop's natural decisions).
- **Cost:** about 1 day of code with the builders. Searched games take 1.7-3.3 s each (measured in `scr-jsearch479` at
  485-498), so about 2-3.5 h at the stated deals and 4-7 h with the doubled deals the power fix needs. It runs with at most
  2 screens live, or overnight.

### H90 · N4, N5 · untested · Judge-variance audit: does a deck's score spread across rule-compliant judges single out the walls?

- **C id:** C21, diagnostic. **Plan:** parked (needs H85's matrices and H86's independent-network judges).
- **Correction to its premise:** with two in-loop judges, mean minus 1·SD over the population equals min(greedy, searched),
  which is #148's min rule. The factors never varied are λ ≠ 1 and a third or later rule-compliant judge (a reset or arm
  pilot). The disagreement statistic itself is not new.
- **Rivals:** R-A8, R-generic, R-collinear.
- **Design:**
  - **When it runs:** only after H85 (J1, J1', J2, J3) and at least H86's wave 1 (W1, P1). Set (b) must include at least one
    independent-network rule-compliant judge (W1, P1 or bal-1); otherwise R-collinear holds by construction, and it does
    not run.
  - **Common panel:** every judge is scored against one common opponent panel (the human-free submatrix as the decision of
    record, the lists as evaluation rows). The deck × judge × opponent table on shared deals comes from an extended
    `probe_matchups.py` or `hodge_audit.py`. No walls-vs-lists SD is taken under judges that play only walls against
    lists.
  - **Fill:**
    - greedy: either about 30-50k greedy games (several CPU-hours beside the screens), or the human-free 12-deck core ×
      4-5 rule-compliant judges at 64-128 games a cell;
    - searched: never filled from greedy games. J2 and J3 are taken only on H85's submatrix, or budgeted separately
      (one-turn k4 d4, hours).
  - **Bootstrap:** the SD ratio is bootstrapped by source population (H82's set A, set B, t60gate).
- **Predictions:**
  - R-A8, differential: a non-wall ranks above the walls under mean - λ·SD where it does not under J2 alone; or the spread
    predicts wall membership after controlling for |greedy - searched| (a partial correlation or logistic fit).
  - R-generic: an SD ratio below 1.5.
  - R-collinear: the rankings equal J2's.
- **Kill rule:** use Kendall τ on the human-free submatrix plus the share of top-quartile pairwise orders flipped relative
  to J2, against a redraw null at the per-cell SE. Drop the idea if both match the null.
- **Distinct from:** H18, H20 and H23 (minimum and pooling rules); anomaly A8.
- **Cost:** 1-2 h of analysis plus the fill above.

### H91 · N3, N11 · untested · Plasticity: does the old pilot learn new decks more slowly than the same policy in fresh weights (A4)?

- **C id:** C22, diagnostic. **Plan:** parked. It costs about 1 day of engineering and 1-1.5 GPU-days, and its prior is
  lowered by #134-#138: the 460-era weights regained about 60 Elo under a varied field.
- **Rivals:**
  - R1 lost plasticity (prior lowered);
  - R2 plastic, signal-limited;
  - R3 data, not initialisation.
- **The new factor:** the weights' initialisation (fresh vs old), with the policy held fixed. It was never varied in H15,
  H16, H55, H56 or H60. #25 was the only earlier fresh-init distillation, and it compared architectures.
- **Design:**
  - **Teachers:** main `seg_0460` (A4's pilot) is the primary teacher; `scr-resetcap` 499 is a second if the budget allows.
  - **Students and controls:**
    - a fresh student distilled on a broad human-free mix (4,000 teacher games: 40% current population, 40% past
      populations, 20% wide), to held-out KL of at most 0.15;
    - control (a): a fresh student distilled on the teacher's own narrow population, to the same KL. This separates data
      (R3) from initialisation (R1);
    - control (b): the teacher with a reset Adam state, so the optimizer state is matched across arms.
  - **Probe B, primary:** 2,000 fresh-Adam steps per arm fitting soft CRN-search targets (H72) on 20k held-out states, 3
    seeds per arm, with written cross-entropy thresholds per rival.
  - **Probe A, secondary:** each arm trains a fixed 30 iterations (no early stop on separation) on 12 held-out coherent
    human-free decks.
    - Every flag is given explicitly: lr 2e-4, epochs 2, deck_mode cross, the adopted shaping and deck-out reward.
    - Games per iteration are stated.
    - At least 2 training seeds per arm (or an A/A teacher replicate), and 2,500-3,000 paired games per checkpoint, or
      the 1.5× criterion is dropped.
  - **Audit:** split at 290 and compared within one architecture; pilot-v2 is a reference only.
  - **Probe C:** on the lists, diagnosis only.
- **Predictions, on level as well as slope:**
  - R1: the fresh student reaches a higher win rate than the reset-Adam teacher at 30 iterations on the 12 held-out decks,
    with lower probe-B cross-entropy.
  - R2: the fresh student is at or below the teacher.

  The gain normalised by headroom is secondary.
- **Kill rule:** if the fresh arm cannot reach KL 0.3 within 10 epochs, record it as the core arm failing (a capacity or
  data limit of distillation, as in #25). It is not dropped silently.
- **Distinct from:** H15, H16, H55, H56, H60; anomaly A4.
- **Cost:**
  - engineering: about 1 day (a deck-source and `--fresh` option for warmstart, a checkpoint adapter for `--init-from`, an
    h2h `--panel-file`, probe-B target generation and fit, the audit);
  - compute: 1-1.5 GPU-days, booked as one screen slot;
  - limits: warmstart RAM sized for 4,000 games (or streamed); `limits.apply` and `limits.cap_workers` in every new entry
    point.

### H92 · N6, N9, N5 · untested · Null-drift accounting: how much of every from-scratch and fresh-head composition drift is the proposal base rate?

- **C id:** C23, diagnostic. **Plan:** parked. Its consumer H110 waits on H109 and H99; it runs in cycle 2, before H110 (4-6
  h of agent time).
- **Rivals:** R-arrival (H27), R-results, R-resist. The bands cover the whole range; ρ_P in 0.6-0.75 or 1.25-1.5 gets a
  pre-written reading (partial arrival with partial resistance or amplification) and a follow-up.
- **The never-done part:** the proposal/selection decomposition for runs before #138 (scr-v2, scr-scratch, 016, and the
  reset runs at 460-463).
- **Design:**
  - **(a) Proposal expectation:** `Drafter.sample` 1,000 times per deck, with each run's own settings, for near-uniform-head
    phases only.
    - Reset-run windows are cut to iterations with logged h_in of at least 5.5 (460-463 for scr-reset, scr-resetcap,
      scr-gamma and scr-judge2), or the learned-head contribution is reported separately through the 469 snapshot.
    - The 017 and 018 fresh heads are read from the per-head log rows, not the aggregate h_in.
  - **(b) Observed change:** the moved share × E[change | moved].
  - **(c) The ratio:** ρ_k for each kind, using the group-change per-deck SD and a bootstrap that resamples decks across
    iterations. The expected SE of ρ is stated before running.
  - **(d) Validation:** the generators fact-check slopes and H94's acc-prop figures for the 479 forks are cited, not
    re-derived. The forks only validate the simulator, adding the forks those sources lack (ctl479 before 486, league479,
    lamv479, vs479).
    - The shape-matched surrogate is validated under group changes on real snapshot decks (460, scr-v2's final, 479-499),
      comparing the uniform-head proposal mean on real decks with that on surrogates.
    - 016 (random moves, no groups) is the null calibration.
  - **(e) Other pools:** the 2005 pool by card-type counts only. The MTG null is dropped (there is no card data; it is
    deferred to H109).
- **Predictions:**
  - R-arrival: ρ in [0.75, 1.25] on every kind in the uniform-head select runs.
  - R-results: ρ_P of at least 1.5.
  - R-resist: ρ_P of at most 0.6.
- **Kill rule:** analysis only. If the simulated proposal mean misses the 479 forks' logged prop by more than 0.3 cards a
  draw after 2 h of fixes, report only the forks' acc-prop.
- **Distinct from:** H27 (descriptive only); H45; H93 and H94 (head-update drift).
- **Cost:** 4-6 h of agent time, a few CPU minutes, and seconds of GPU for the views.

### H93 · N6, N5 · untested · Draft-head bench: replay the exact head on frozen 479 views with null and planted rewards (drift or signal, incoming and cut choice)

- **C id:** C24, diagnostic. **Plan:** item 9 (a head-only GPU probe, about 3.5 dh; stage 2 adds about 3 dh).
- **Rivals:**
  - H-drift;
  - H-signal;
  - H-overreact;
  - H-view, added: most of the logged fall in h_in comes from the deck distribution, not the head's parameters.
- **Design:**
  - **Snapshot:** `runs/screens/scr-resetcap/population_it0479.pt` (h_in 2.745), loaded with its draft optimizer state
    (Adam step 20 restored, as the forks did). A fresh-Adam arm is a separate factor.
  - **Replay:** views from `Drafter.view` (a field of 4), 20 steps with the exact Drafter code (6 swaps, floor 3, group
    0.3, draft-lr 3e-4, entropy 0.01). K = 3 at 10 games (as ctl479) and K = 1 at 20 (as the gate), with Bernoulli results.
  - **Arms, 5 seeds each:**
    - N: null rewards;
    - P_card(δ): for the 479 favourite card, and separately for an unfavoured Trainer;
    - P_kind(δ): +δ per Energy added and -δ per Trainer cut;
    - P_in(δ): value on the incoming card only;
    - one null arm that moves decks at the null rate with recomputed views.

    δ ∈ {0.005, 0.01, 0.02, 0.05}.
  - **H-view arm:** the frozen 479 head on ctl479's 484/489/494/499 views, and ctl479's saved heads on the fixed 479 views.
    This splits the logged fall into a deck part and a parameter part; the bench is compared with the parameter part, not
    the logged h_in.
  - **Noise:** the measured seed SD of h_in at step 12 is reported.
  - **Code:** `op_audit.py`, copied from the 9afecfab session's `meta_lens` first.
- **Predictions, disjoint at δ = 0.005:**
  - H-drift: null h_in at most 1.5 by step 12 in at least 4 of 5 seeds (at least 60% of the parameter part of ctl479's
    fall), and the cut's Trainer share at least 1.15 times the copy share with no signal.
  - H-signal: null h_in of at least 2.5 through step 20 and a cut ratio of 1.08 ± 0.03; no collapse at 0.005, and the
    first collapse at δ in [0.01, 0.03].
  - H-overreact: collapse (h_in below 1.0 within 20 steps) at δ = 0.005, with the KL per update unchanged between 0.005
    and 0.05. Given #92's real single-card effects of 0.006-0.03, a collapse at 0.005 reads as overreaction only if the KL
    does not scale with the signal-to-noise ratio.
  - H-view: most of the logged fall is deck distribution.
- **Kill rule:** a fixed plan. A null ending at 1.5-2.5 nats, or a seed SD above 0.3 with the result within 0.5 nats of a
  band edge, is unresolved and goes to H94. Stage 2 is skipped under H-signal with δ* of at least 0.01.
- **Stage 2, only under drift or overreaction (2-3 h of code):** plain SGD; Adam with eps 1e-3 or β2 0.9; updates pooled
  over 3 steps; a significance-gated per-card history; a KL trust region; a frozen copy-uniform cut under P_kind; and
  winner-only credit with H111's random-one credit control.
- **Distinct from:** H30-H34 (entropy amount or step size inside screens; the optimizer swap is untested); the critic's gap
  on the cut choice (no family covers it).
- **Cost:** 3 h of code and 1 GPU-hour.

### H94 · N6, N5, N4 · untested · Does the head's learning amplify a weak judge preference? Frozen-head and null-reward-head forks from 479

- **C id:** C25, diagnostic. **Plan:** item 15, conditional: it runs if H93's null arm ends at 1.5-2.5 nats or seed noise
  leaves it unresolved. 2 slots (+1 for F0r), about 6 dh.
- **Rivals:**
  - H-amplifier;
  - H-judge-alone;
  - H-S-intrinsic;
  - H-encoder, added: proposals drift through the pilot's representation or the field context.
- **Design:**
  - **Forks:** F0 runs `--draft-lr 0` (the 479 head frozen). N0 runs `--draft-null`, its rewards permuted across draws
    within each iteration (about 20 lines). Both use `--reseed 3` against H98's seed 3, the matched control (same fork,
    recipe, code hash and workers).
  - **Optional F0r:** `--draft-reader-frozen` (about 30 min of code): the head reads through a frozen copy of the 479
    pilot while PPO trains the playing pilot. It runs as the third screen or afterwards.
  - **Flags:** scr-gate479's config values passed explicitly (draft_lr, draft_ent 0.01, draft_h_in_floor 3,
    draft_group_p 0.3, practice_games 250, lr 2e-4, epochs 2, shaping 0.1, swaps 6).
  - **Fixed-reference proposal readout:** each iteration, or offline over population_it0484/89/94/99.pt and
    checkpoint.pt. A frozen panel (the 479 decks and a fixed 479 field sample) is scored with the current head and current
    encoder, then with the current head and the frozen 479 encoder. This splits proposal drift into head learning, encoder
    drift and deck-state drift.
- **Predictions:**
  - Amplifier: fixed-panel prop |Pokémon| below 0.3; Chansey+Snorlax at most 60 at 499, against a control-like spread of
    73-80; median Trainers at least 27.
  - Judge-alone: F0 tracks the control, with acc - prop of at least +0.8 Pokémon.
  - Intrinsic: N0's h_in falls at least as fast as the control's (about 1 nat over 20 iterations), with fixed-panel prop of
    at least +1 Pokémon.
  - Encoder: F0's prop drifts by at least +1 Pokémon while F0r's stays below 0.3.

  A Chansey+Snorlax count of 61-69 at 499 is partial amplification.
- **Kill rule:** both forks run to 499 unconditionally. F0 stops at 489 only if its fixed-panel prop already matches the
  control's drift (the freeze did not hold). Never kill on a Chansey+Snorlax count at or above the control's at 489.
- **Distinct from:** H33 (lr never set to 0; no null-reward control); H30-H32 and H34; H26's verifier (acc/prop analysis
  missing); H35 (the reading path); H93 (offline).
- **Cost:** 1.5-2.5 h of code and 4-6 slot-hours.

### H95 · N5, N6 · untested · Paired common-random-number re-test of the head's proposals: their true effects, the gate's precision, and whether pairing pays

- **C id:** C26, diagnostic. **Plan:** parked. It shares the aligned builder with H89's (h) arm; both run in cycle 2, after
  H72.
- **Rivals:** H-noise-walk, H-real-selection, H-pairable, H-divergent.
- **Design:**
  - **State and candidates:** `scr-t60gate479/population_it0494.pt`; 60 decks (30 inside and 30 outside the wall cluster);
    one 494-head candidate per deck.
  - **Builder:** position-aligned (it bypasses pool.names, with the group-change mapping), shared with H89. H89 reuses
    these candidates and paired games, and ρ is reported once.
  - **Opponents:** sampled as the loop samples them: many distinct population incumbents (for example 100 opponents × 2
    seats, one deal each, or at least 25 opponents). Each candidate game is paired with its incumbent's game by (opponent,
    seat, seed), with a maxTurns 60 pass-through.
  - **Divergence:** the first decision at which incumbent and candidate trajectories diverge is logged, with whether it
    comes before any changed card is seen; the pilot conditions on both decklists.
  - **True effects:** their distribution comes from deconvolution or empirical Bayes (observed variance minus mean sampling
    variance; a normal-mixture or NPMLE prior). The criteria are stated on the deconvolved quantities, and the 0.05-0.08
    zone has a pre-registered reading.
  - **Gate precision, non-circular:** acceptance is simulated on held-out games (40 of the 200 per side for the gate, 160
    for truth), or computed analytically from binomial noise at 20.2 games a side against the deconvolved effects.
    Precision is reported as the posterior P(δ > 0 | accepted).
  - **Composition:** δ is regressed on two of dP/dT/dE (for example dT and dE), and the slope SE achieved is reported.
- **Predictions:**
  - H-noise-walk: a deconvolved SD of true effects of at most 0.05; at least 70% within ±0.05; precision at most 0.65;
    slopes within ±0.01 a card.
  - H-real-selection: an SD of at least 0.08; at least 30% beyond ±0.05; precision at least 0.8.
  - H-pairable: pooled ρ of at least 0.3, and a paired variance at most 0.7 of the unpaired.
  - H-divergent: ρ below 0.15, a variance ratio above 0.85, and divergence before any changed card is seen.
- **Kill rule:** after 20 decks, stop if ρ is below 0.1 and the SD of δ is at most 0.04. Build no paired gate if the
  variance ratio exceeds 0.85.
- **Distinct from:** H24 and H25 (unpaired noise and gate); H89 (designed variants, not proposals).
- **Cost:** 4-5 h of code, and about 24,000 greedy games: 1-1.5 h at about 6 workers beside the screens.

### H96 · N5, N7 · untested · Solution-concept dynamics on measured matrices: which population rule keeps a cyclic field?

- **C id:** C27, diagnostic. **Plan:** parked. Its J1 arm is a positive control, and its consumers (H101, H112, H113) are
  parked; it runs after H85's stage 1 supplies the human-free panel.
- **Scope:** this is the measured-matrix first stage of H101's rule screen (the same rules R1, R3, R4), so the two are not
  logged as separate tests of one mechanism.
- **Rivals:**
  - H-judge-bound: the J1 arm becomes a positive control, reporting the share of bootstrap draws in which pop829 stays a
    Condorcet winner over the human-free panel.
  - H-truncation-collapse: under J4 (pilot-v2).
  - H-noise-holds.
- **Design:**
  - **Simulator:** numpy, on matrices already on disk (J1: `jf2_human24_resetcap499.json` + `resetcap499_own_vs_own.json`;
    J4: `jf2_human24_v2.json` + `resetcap499_v2_vs_v2.json`), completed from H85's panel. 99 decks, about 20 games a deck
    an iteration, results drawn from bootstrap matrices.
  - **Rules:**
    - R0: includes the `--select` move. Each deck proposes one other strategy, weighted by card distance (for example
      exp(-d/6)), and moves when that strategy's sampled score beats its own at z 1.0. Turnover's 1 in 4 is a
      10-card-distance mutant of a best-quarter deck. The move rate is checked against the logs (13-28 an iteration
      under the gate).
    - R1: QRE allocation;
    - R2: max-entropy Nash;
    - R3: a torus;
    - R4: ε-lexicase;
    - R5: replicator dynamics.
  - **Timescale calibration:** R0 under J1 must reproduce the logged rise of the wall cluster (scr-gate479: 53 to 73 decks
    with both walls over about 20 iterations).
  - **Controls and seeds:** a neutral-drift control (all off-diagonal payoffs 0.5) for every rule; the seed SD is measured;
    100 seeds per cell.
  - **Elites:** from scr-t60gate479's population_it0494.pt or checkpoint.pt (498 was never saved). "Non-wall" is defined by
    k-means on card counts or a Chansey+Snorlax marker.
  - **Pre-checks:**
    - confirm that scr-resetcap's checkpoint.pt and population_it0499.pt hold the same pilot weights before merging the J1
      matrices;
    - compute the human-free submatrix's cyclic (Hodge) share first, and if it has no cycle, say in advance that the
      human-free decision cannot separate the rules; per-rival predictions are written for that submatrix.
- **Predictions:**
  - J1: every rule ends with the walls at 85% or more in most seeds (the positive control).
  - J4, H-truncation-collapse: R0 reaches an effective number of at most 1.6 within 100 iterations in at least 75% of
    seeds, while R1 at λ 5-10 holds at least 3 archetypes with TV at most 0.2, and R3 keeps at least 3 domains.
  - J4, H-noise-holds: R0 keeps an effective number of at least 2.5 for 300 iterations, within 0.5 of R1.
- **Kill rule:** a fixed diagnostic. A rule that fails to keep at least 2 archetypes under J4 gets no system screen.
- **Distinct from:** H39 (the built cap); H44 (Nash-PSRO, #26-40, collapsed); JF2 (S35); H85 (audits the judge itself).
- **Cost:** half a day of CPU code, plus 30-40 min of completion games unless H85 supplies them.
- **Evan:** the torus (R3), lexicase (R4), QRE and Nash allocation need his rule-3 approval before any system screen.

### H97 · N6, N7, N5, N4 · untested · Valley test: fitness along block-wise edit paths from the walls to human archetypes

- **C id:** C28, diagnostic. **Plan:** item 14, greedy stage (tier B, about 5.5 dh). The searched J3 subset waits for H72.
- **Prior points:** #127's probe-hitmonchan and probe-chan-buzz are the only earlier landscape points. They showed no valley
  at 8 cards under pilot-v2, and a monotone decline under the population pilot. What this adds: paths to actual human
  lists, block orders, more judges, and field (a).
- **Rivals:** H-valley vs H-open, where H-open means climbable under the loop's actual acceptance rule. H-judge-blocks is
  dropped as already decided.
- **Design:**
  - **Endpoints:** the 3 resetcap 499 walls to Graham Haymaker (0.375), Lieu Wigglytuff (0.396) and Knight Clefable
    (0.583). Endpoint games are kept apart from selection games.
  - **Blocks:** whole evolution lines (7-8-card lines such as Wigglytuff and Clefable split basic-first, so every step is
    at most 6 cards and leaves no orphan evolution), special Energy, each Trainer's copies, and basic Energy in fours. Each
    step's realised P/T/E is logged.
  - **Orders:** 3 fixed orders plus a greedy best-next-block order.
  - **Deals:** common deal seeds per opponent across every deck of a path, analysed as paired step differences.
  - **Fields:** (a) the 12 best decks of resetcap 499; (b) the 24 lists, field-weighted.
  - **Judges:**
    - J1 (499 greedy) on field (a) is the primary cell: Graham and Lieu already beat the walls under J1.
    - J4 is pilot-v2 for now (H86's W1 only after H86).
    - J3 only after H72 (and H70/H82 for the STS rule), or a plain draw at 60 as a stated stand-in. It is never run on the
      CPU path (about 22 h).
  - **Early stopping:** none for greedy judges, so full paths are evaluated; early stopping is kept only for the searched J3
    subset.
- **Predictions:**
  - **Valley depth, bias-corrected:** fresh-deal re-evaluation (at least 576 games) of the argmin deck and both endpoints,
    or the interior mean against the chord, with thresholds set from a simulated noise-only null at the measured SE.
  - H-valley: every order, the greedy best-next-block order included, dips below the chord beyond the null's 95th
    percentile, confirmed on fresh deals.
  - H-open: each step's gain clears the gate's minimum detectable gain (about 0.11-0.16 at z 1 and about 20 games), or the
    path has at least 1 expected gate pass per step.
- **Kill rule:** none for the greedy stage.
- **Distinct from:** H28 (group changes, an operator rather than a landscape measurement); H27; the X link was never tested
  directly.
- **Cost:** 3 h for the builder and 4-5 GPU-hours (8-12 games/s on wall games, about 2-2.5 h per judge, beside the screens).
- **Generality:** any operator that follows from H-valley must define its blocks game-agnostically, not as Pokémon
  evolution lines.

### H98 · N12, N5 · tested (#153) · Three-reseed A/A of the gate recipe at 479: the noise floor for the escape regime, and a replication of the one positive lever

- **Result (#153, grade A on its registered bands):** H-noise + (pooled 3-df upper bounds 3.09 cards and 13.1
  wall-core decks; point SDs 1.06 and 4.5, at the attractor's edge), H-attractor -; gate real not met as registered
  (largest type gated minus ungated -31.9 [-49.0, -14.8], the bound nearer zero short of 20), gate luck -. Distance -5.8
  [-9.4, -2.3] and wall-core -18.2 [-29.6, -6.8]. Every 479 arm is inside the upper bars on every readout and no arm
  moved wall-core past the point bar (S36). Do not repeat: `scr-gate479`'s command with `--reseed` 3 or 4
  (`scr-gate479-s3`, `-s4`); a fourth seed is the variant that narrows the bound.
- **C id:** C29, diagnostic. **Plan:** item 5 (2 screen slots, about 4.5 dh).
- **Rivals:** H-noise vs H-attractor; H-gate-real vs H-gate-luck.
- **Design:**
  - **Runs:** `--reseed 3` and `--reseed 4`, from the exact command at the top of `runs/screens/scr-gate479/stdout.log`,
    changing only `--run` and `--reseed`. `--keep 5` puts snapshots at 484/489/494/499.
  - **Config check:** before reading, diff each `config.json` against scr-gate479's; only run, reseed and stop_file may
    differ.
  - **Shared control:** seed 3 is also H94's matched control.
  - **Readouts:**
    - the pairwise per-iteration trajectory RMS over the 3 gated pairs (distance, wall-core, largest type, moves), pooled
      with ctl479 vs resetcap into a 3-df within-recipe SD;
    - each 479 arm re-read against the upper confidence bound of that pooled SD;
    - wall-core (Chansey+Snorlax) decks at 484-499 as the primary type readout, with the overlap type secondary (H64);
    - the two final-pilot walls verdicts (15-30 min of GPU each).
- **Predictions:**
  - Noise: the pooled SD's upper bound is at least 3 cards (window distance) or at least 10 wall-core decks.
  - Attractor: at most 1.5 cards and at most 5 decks.
  - In between (1.5-3 cards or 5-10 decks): inconclusive; keep the 2.0-4.8 band.
  - Gate real: the Welch 95% CI of gated minus ungated largest type excludes 0, and its bound nearer zero is at least 20
    decks below.
- **Scope of claims:** only whether the 479 arms' nulls are real nulls. It does not decide "escape is impossible" or "move
  to fresh starts".
- **Kill rule:** none (an A/A); a crashed run is resumed. Optionally, extend the two new runs to 509 and read only whether
  wall-core passes the ungated 499 level.
- **Distinct from:** H42 and H62 (the A/A runs at 160 only); H25 (the same configuration, but on the never-run seeds 3 and
  4).
- **Cost:** 3.5 slot-hours, 0.5 GPU-hours and 0.5 h of agent time.

### H99 · N9, N8, N10 · tested (#157, #160) · Pilot-first warm-up W: plain-result PPO on rules-generated wide decks until games end by the game's own win conditions

- **Result (#157):** H-bootstrap-ok + (criterion at iteration 8 and 9; deck-outs 45% -> 7-10%), H-bootstrap-stall -. The
  criterion's decisive endings are 79-82% benching out on 8-Pokémon wide decks, with Prize endings at 10-11%. H5 / H1
  unread: W is -18 / -19 Elo against pilot-v2 on held-out wide decks but -489 / -449 on the 24 lists. JF1 0.59 at the end
  (0.61 at it9), with the walls winning by Prizes and benching (31-32 deck-out wins of about 1,350), a low-skill reading.
  Do not repeat: the C30 command with seeds 1-2 stopped by the ending monitor; the open variant is W trained on to
  competence on the lists (registered in `runs/pilot/C30/record-cont.md`).
- **Result, continuation (#160):** W2 from 19 to 119: Closing + (lists Elo −449 → −345 at 39, −320 at 79, −274.5 at
  119); Competent, No transfer and Stall -. Held-out wide +46. JF1 0.52-0.57 throughout, so H5 / H1 stay unread. Training
  games end 76-81% by no Pokémon and 12-20% by Prizes: the practice is not a Prize race. Do not repeat: W2 trained on
  past 119 with the same flags and decks without a new factor (the slope is about 70 Elo per 80 iterations).
- **C id:** C30, intervention (the prevention start). **Plan:** item 6 (1-2 slots, about 6.5 dh).
- **Rivals:** H-bootstrap-ok vs H-bootstrap-stall. By-product judge rivals: H5 (JF1 at least 0.55) vs H1 (at most 0.35).
- **The never-varied factor:** the training-deck distribution: full-pool `wide_deck`, against meta-99's drafted decks in
  #70-#73 and the 56-card wide decks at deck-out 0 in #42/#48. The attack gate mostly replicates #70-#73 and is kept only as
  a stopping rule.
- **Design:**
  - **Decks:** `notes/scripts/pilot_decks.py` switched to the full 277-card pool and `rl.decks.wide_deck` (512 decks,
    2,048 pairs).
  - **Command, in full:** `rl.train` from random init: `--model tokens --d 256 --tok-layers 4 --heads 8 --deck-mode cross
    --lr 2e-4 --epochs 2 --ent 0.01 --lam 0.95 --gamma 1 --shaping 0.1 --shaping-iters 100 --deckout-win 1`.
  - **Count features:** off, to avoid the live bug. The confound this creates with H110's pilot factor is recorded, unless
    H77's fix is applied to both.
  - **Seeds:** W1 and W2, run in parallel in 2 of the 3 slots or one after the other (state which).
  - **Stop monitor:** at least 70% of games end by Prizes or no Pokémon, and at most 25% by deck-out, for 3 consecutive
    iterations; then 10 more iterations; cap 60.
  - **Prior, before training:** JF1 (3 walls × 24 lists, 16 a pair, #147's deals) on the existing `runs/abl` deck-out-1
    checkpoints (base it79, base-s2 it79, deck-cross it39, no-deck), shared with H76.
  - **Evaluation:** JF1 and a head-to-head against pilot-v2 (on the lists, evaluation only, and on held-out wide decks) at
    it20, it40 and the end. JF2 at the end only, as a sanity check.
- **Predictions:**
  - Ok: the criterion is met by iteration 40 or earlier in both seeds.
  - Stall: deck-outs of at least 50% and Prize endings of at most 30% at iteration 40.
  - H5: JF1(W) at least 0.55.
  - H1: JF1(W) at most 0.35.

  H5 and H1 are read only when W is within about 30 Elo of pilot-v2 on the lists. JF1 rising with competence means stall
  was learned (H5, H51); falling means low skill.
- **Kill rule:**
  - At least 50% deck-outs at 60: the bootstrap failed, so start the margin fallback (H104's code).
  - 25-50% at 60: continue to 90, as chosen in advance.
  - JF1 in 0.40-0.55: a third seed, or the better seed continued to about 120.
- **Distinct from:** H45 (its untested "pilot first on wide decks"); H46 (remedy a); H86's W1 (a pilot-v2 fine-tune, not a
  random-init pilot).
- **Cost:**
  - 30-45 min of code;
  - about 2-3 h per seed beside two screens (about 1-1.2 h on an idle machine);
  - evaluation: about 1.5-2 CPU-hours over both seeds (JF1 at 1,152 games plus about 800 head-to-head games at it20 and
    it40, each seed).
- **Evan:** the method status of `wide_deck` waits on H109, Q3. Until then this is a diagnostic.

### H100 · N5, N6, N7, N4, N8, N9, N1 · untested · Is the human field a fixed point of the loop? The seeded 24 lists plus wall invaders, under frozen, learning, clocked, fresh and walls-trained pilots

- **C id:** C31, diagnostic, quarantined. **Plan:** parked. `notes/method.md` section 7 puts the offline fixed point (H85)
  first. Wave 1 is about 8 slot-hours plus 2-3 h of scripts, and its R arm is predictable from JF1; cycle 2, after H85's
  stage 1 and H99.
- **Rivals:**
  - H-reach/R-fixed;
  - H-wrong-fixed-point;
  - R-judge;
  - H-clock;
  - H-arrival-drift;
  - H-judge-shape-bias;
  - H-convergent-collapse;
  - R-co-adaptation.
- **Design:**
  - **Snapshot:** in `population_it0479.pt` format. It holds 'drafter' (any head; `--draft-reset` discards it), iter,
    config, and net (pilot-v2 it349, or the arm's pilot). Each deck has id, deck, born, parent=None, kind='seed:<list>',
    sum=0, n=0, with born no later than iter+1-protect.
  - **Population:** the 24 lists × 4 plus the 3 walls as single invaders, with a fresh head.
  - **Launch and logging:** `--reseed`, with `--save-every 1` or a lineage dump each iteration. `lineage.py` is written: the
    96 seeded ids persist through accepted moves, and mutant descendants are traced through 'parent'. Wide entrants are a
    stratum of their own, never in the population median. Every hand-set flag is written out (lr 2e-4, epochs 2, swaps 6,
    draft-lr 3e-4, draft-margin 0, shaping 0.1, h-in-floor 3, group 0.3).
  - **Wave 1, dependency-free once the snapshot exists:**
    - F: frozen pilot-v2.
    - A: pilot-v2 plus a 10-iteration burn-in with the decks frozen and 250 wide practice games.
    - R: the scr-resetcap 479 pilot. R is a positive control, since JF1 predicts invasion; its static walls probe cites
      #137/#147, with no new games.

    Frozen arms run with turnover off (`--turnover-every 0`) plus a mutants-only variant, or with seeded decks older than
    `--protect`, and the mechanical removal count is stated.
  - **Shared and dropped arms:** Fq is H110's seeded-field cell, run once and reported in both. C is dropped if it would
    duplicate F.
  - **Wave 2, once prerequisites land:**
    - B: A under H70's rule, with T from H71, or 60 as a stated assumption.
    - W: H99's pilot.
    - A from H86's H1.
  - **Invasion, defined by origin:** wall-core (Chansey+Snorlax) decks that are descendants of the 3 invaders, seeded decks
    converted by accepted moves (only these two count for H-wrong-fixed-point), or wide entrants.
  - **Decision table, written first:** maps each combination of F/Fq, A, W/R and B outcomes to a rival. A hold in a learning
    arm at 20-30 iterations only bounds the invasion rate.
- **Predictions:**
  - H-reach: Chansey+Snorlax at most 6; accepted moves at most 10% of decks an iteration; acc-prop below 0.3 a move, or
    pointing back to the seed; at least 70% of the surviving seeded-lineage decks keep overlap of at least 0.5; at least 6
    of 8 archetypes keep at least 3 decks; median P/T/E within ±2/±3/±2 of 13.5/28/18.
  - H-wrong-fixed-point: the start pilot rates the walls at least 0.55; the walls spread (Chansey+Snorlax at least 25 by
    30, at least 10 wall-core decks by 20); accepted moves add Pokémon or Energy and cut Trainers by at least 0.5 a move.
  - The other rivals keep the candidate's bands (C31 in `notes/data/cycle1/candidates.json`).
- **Kill rule:**
  - Stop an arm when Chansey+Snorlax reaches 40, or when retention is below 30% at 10.
  - Frozen arms stop at 10 if median Pokémon rose by 6, Energy by 5, or the wall cluster holds at least 10 decks.
  - B stops if time-ties exceed 60% for 3 iterations.
  - Any arm stops after 20 if the gate moves fewer than 5 decks for 5 iterations with no drift.
- **Distinct from:** H17 and H19 (fixed lists on one side of games, never drafted or invaded); H20 and H46 (scr-v2); H04
  (plain draws from walls); H85 (the offline version). No run has ever seeded the population with the human field.
- **Cost:** snapshot and lineage scripts take 2-3 h. With H70, H86, H99 and H110 needed before wave 2 and Fq, it takes 2-4
  days elapsed.

### H101 · N5, N6, N7 · untested · Surrogate metagame testbed on top of the head bench: screen selection and population rules in seconds

- **C id:** C32, infrastructure. **Plan:** parked. It costs 3-4 days of code plus 1-3 GPU-days, and its prerequisites H93,
  H95 and H85 are unmet.
- **Scope:** H96's strategy-level results for R0, QRE, the torus and lexicase are taken as given. This screens only what
  needs the real draft operator and edit-level payoffs: head-rule interaction and valley crossing. (#138 logged observed
  move rates; it was not a null simulation.)
- **Rivals:** H-static vs H-coadapt.
- **Design:**
  - **Payoff model:** P(i beats j) = σ(r(x_i) - r(x_j) + a(x_i)ᵀ Ω a(x_j)) + β × cluster share. It is fitted on games from
    the judge being validated: the 479 pilot, sampled and untimed, with H95-style edits around the 479 population (10-20k
    extra games). A second fit uses a later snapshot (494 or 499) of the same lineage.
  - **Measuring β:** directly, by rating a fixed deck panel under pilot snapshots 479-499 and regressing on cluster share.
    The fitted-dynamics β is only a cross-check, with a seed-bootstrap CI that must exclude 0. β is fitted together with a
    misfit alternative (a higher-rank Ω, or per-cluster offsets), and β > 0 must survive it. There is no round of model
    fixes after β is fitted.
  - **Baseline:** "an edit has its parent's rating", on held-out edits (split by edit or by deck), with a 2% log-loss bar.
  - **Valley anchor:** 2-3 measured interpolation paths (from the walls to a self-generated non-wall elite, every 2 cards,
    against a fixed field), which the surrogate must reproduce within its CI before valley crossing counts.
  - **Code:** selection, turnover and cap logic are extracted from `rl/metagame.py main()` into functions, with a parity
    test replaying a logged ctl479/gate479 iteration's decisions. The head is the 479 head with live REINFORCE updates
    under surrogate rewards, Adam restarted as at a fork. The frozen-feature CPU proxy is for smoke tests only.
  - **Staging:** 5 seeds × 30 iterations for every rule, then 20 × 50 only for finalists, with the seeds' views batched.
  - **Move rates:** not used as evidence of validity (they match the null rate).
- **Predictions:**
  - H-static: β about 0 and unchanged ratings across snapshots. The relapse timing reproduces within the observed
    ctl479/resetcap replicates ± the A/A spread, and the gate's slower drift reproduces at the same β.
  - H-coadapt: the wall advantage grows with share, with β > 0 surviving the misfit term.
- **Kill rule:** abandon if held-out log-loss is not at least 2% better than "edit = parent". A rule that fails the
  surrogate gets no system screen.
- **Distinct from:** H68 and H69 (surrogates that ranked or searched decks and were exploited; this one only screens
  methods); H96.
- **Cost:**
  - 3-4 days of code, including the extraction, with H93, H95 and H85 as prerequisites;
  - about 8 s a surrogate iteration;
  - 2-3 GPU-hours per rule-β at 20 seeds × 50 iterations, run with fewer than 3 screens live or with capped GPU memory.

### H102 · N1, N4, N12 · untested · Evan's decisions on the game's specification: the round rule (training, judging only), how T is fixed, commits and engine fixes

- **C id:** C33, decision for Evan. **Plan:** item 4, sent with H109 as one message (about 1 dh).
- **Evan:** these choices are his (rule 4). No workflow message, including the relayed "cheaper spend" reply, stands in for
  his consent on D1 or D2.
- **Rivals:**
  - the safety-net reading (request 24: a limit only guards against games that never end) vs the specification reading
    (the lists are optimal for 20-minute rounds decided by Prizes at time);
  - from H89: R-draw-haven, R-rule-irrelevant and R-search-needed.
- **The message:** a follow-up that quotes requests 24 and 26 and asks only what was never asked.
  - **D1, (a') judging only:** may an unfinished judged game at turn T be decided by Prizes, as the 2000 event scored it
    (a time win 2/3, a Prize tie 1/3; pilot seat points +1 / +1/3 / -1/3 / -1)? It is asked with the new evidence: exact
    re-scoring of 576 greedy games puts the walls at 0.48 of STS points at 20, 0.55 at 40, 0.62 at 50 and 0.67 at 60, while
    #139's end-of-game proxy gave 0.64-0.66 and is biased toward the walls, not just noisy. D1 (a), training and judging, is
    asked again only with that evidence.
  - **D2, only if D1 is yes:** how T is fixed: from H71's documented round length, frozen before any run; from the game's
    own self-play length; or drawn per game from a stated prior. Never by its effect on distance to the lists (#147 chose
    50-60 after seeing the flip).
  - **D7:** commit go-ahead for the work since fa32895 (#127): 27 uncommitted paths, 15 modified files, +1,361 lines.
  - **Engine fixes behind default-off flags:** the ending label, and #139's verified deviations.

  D1 (b), evaluation only, is dropped: evaluation use needs no approval. D3, D5 and D8 are decided in the loop and logged.
  D6 (hiding opponent lists) is held until H78 reports. Evidence comes from runs with an exact prizeTrace only.
- **If (a') is approved, its arm:**
  - a matched control: a plain draw at the same T, same fork, recipe and seeds (common random numbers where possible);
  - JF1 under the arm's judge, scored with the arm's rule, at start and end;
  - `--judge-explore` required, or recorded games excluded from deck scoring explicitly;
  - reading: stopping at 489 can only confirm or refute the acc-composition prediction; a null type readout at 489 is
    inconclusive, since relapse takes 10-15 iterations;
  - engine cost: half a day to a day (a per-job maxTurns in `env/runner.js`, a Prize-decided time ending in `env/game.js`,
    fractional scores through `judged()`/`judged_mean`, the draft reward, turnover and the judge_search path, with engine
    tests).
- **Predictions, an action for every answer:**
  - specification reading: H103 opens, with T fixed by D2;
  - safety-net reading: the walls' edge must be removed by pilot or judge strength (about 0.57 against the lists today,
    #147);
  - a conditional yes: its condition is logged and acted on;
  - no D1 answer: the rule stays evaluation-only.
- **Kill rule:** D1 (b) or (c) drops H103. D1 (a') is asked only if H89 shows a reading difference of at least 2 SE (or
  with a searched judge, under R-search-needed).
- **Distinct from:** H03, H04, H23, H29, H44 and H51 (the Prize decision was never trained); #139's Next asked D1 once, and
  Evan chose a plain draw.
- **Cost:** about 1 h of writing and one message of Evan's time.

### H103 · N1, N2, N4, N10 · untested · Training-side test of the round rule: the pilot on frozen decks under the STS rule, against a plain draw and no clock

- **C id:** C34, intervention. **Plan:** parked.
- **Evan:** not launched until Evan explicitly approves the rule in training (H102, D1 a) and the source of T (D2). The
  relayed "cheaper spend" message is not that approval.
- **Rivals:**
  - CA clock-aware racing;
  - TC competence-bound, tested as an equivalence (TOST) at a stated margin;
  - TU turtle;
  - DS draw-seeking;
  - field exposure, added: the frozen field, not the clock, sets what the pilot learns.
- **Design, stage 1 (decks frozen):**
  - **Setup:** `--freeze-decks`; fork the scr-resetcap 479 pilot with `--reseed 2`; 250 wide practice games; 500 recorded
    games; no judge games.
  - **Arms:** A_sts (the rule, with per-seat points), A_draw (the same clock, plain draw) and A_none (untimed); 2 seeds of
    A_sts and A_none from the start; 25 iterations.
  - **T:** as D2 decides. Either per game from H82's Π with a time-left feature ((T - turn)/48, zero-initialised), or a
    fixed T* with no time-left feature.
  - **Field-exposure arm:** a second frozen deck set from the population's own decks (for example scr-gate479's
    near-human-shape population, or a type-capped field) as an extra A_sts/A_none pair. Otherwise, report each arm's
    Prize-win turns and time share on the 250 wide practice games and on the non-wall decks.
  - **Judging, fixed in advance:** one T or H82's grid; the same seeded deals for every arm and checkpoint (common random
    numbers); both wall sets.
  - **Flags, not kills:** time endings above 60% is a logged flag (the TU and DS signal). The value-loss-doubling kill
    exempts the first 3 iterations after the reward switch.
  - **Control:** a concurrent from-scratch control on current code, with every adopted flag written out, not the historical
    016.
- **Stage 2,** only if CA holds and H84 does not show SW: the gate recipe with the rule from 479 (control: the same recipe
  without it), and #124's recipe from scratch with the rule beside a concurrent from-scratch control. That is 4 runs,
  about 8 slot-hours. Add search judging if H82 says ExP.
- **Predictions:** the bars come from the SD of a difference between pilots (about 0.031), and 0.03-0.08 is pre-registered
  as inconclusive.
  - CA: at 504, A_sts's pilot gives the walls an STS share at least 0.08 below A_none's under the same rule, and the lists'
    median Prize-win turn at least 4 turns shorter. A_draw changes at most half as much.
  - TC: A_sts within the equivalence margin of A_none.
  - TU: time wins above 30% of the walls' wins and rising; A_sts rates the walls at least 0.03 higher.
  - DS: A_draw's time endings rise by at least 10 points on frozen decks.
- **Kill rule:** as in the candidate, with the changes above; stage 2 is skipped under TC or TU.
- **Distinct from:** H04 (plain draws in the full loop); H51, H52 and H53; H23; H46; H83; H100's arm B.
- **Cost:** 5-7 h of code beyond H70: the glob-shape migration (padding the glob Linear with zero columns), ONNX re-exports,
  per-job T in `env/runner.js` and `env/remote_worker.js` (tsearch clones included), and seat rewards at `runner.js:76` and
  `remote_worker.js:413`. Hard prerequisites: H70, H79, H82 (Π, set B, the grid) and H102.

### H104 · N10, N2 · untested · Prize margin as the pilot's terminal reward: is the human field slow because a slow win pays like a fast one?

- **C id:** C35, intervention. **Plan:** item 13 (tier B, 1 slot with the arms run in sequence, about 6 dh). It requires
  H79's stage 1 (the tempo panel) first.
- **Rivals:** R1 objective, R2 competence, R3 the margin pays the walls.
- **Design:**
  - **Code (about 30-40 lines):**
    - in `env/runner.js` `finish()`, `left()` moves before the reward loop. Reward = (1 - w)·result + w·(Prizes taken -
      Prizes conceded)/6, for every ending;
    - w is threaded through every Runner construction in `remote_worker.js` (and qprobe's z if probes are used), and
      through the `train.py`/`metagame.py` flags and message fields;
    - `aux_targets`' treatment of the margin is decided explicitly;
    - a unit test on fixed endings: a 6-0 Prize win, a deck-out win while leading, a deck-out win while behind, a draw.
  - **Testbed:** human-free, built here unless H77's step 2 builds it first: the 499 population, other types from
    snapshots, and wide decks. Every architecture and PPO flag of the 499 pilot is pinned (deck-mode cross, d 256, 4
    layers, lr 2e-4, 2 epochs, the same `--shaping`).
  - **Arms:** the control (w = 0) in two seeds (the testbed A/A), w = 0.5, and w = 1 (required, for a dose-response). Run in
    sequence or at about 7 workers each, evaluated on common seeds.
  - **Manipulation check, per iteration, from each arm's own sampled games:** the mean final Prize margin of wins, the
    deck-out share of endings, and the value head's correlation with the final margin. If these do not move, the result is
    "not delivered", not R2.
  - **Readouts:** H79's tempo panel; the walls' verdict with the 2 × 2 seat decomposition; Elo against the control; the
    walls' deck-out-win Prize-lead share (baseline 109/148) and their Prize-win share in the verdict games.
- **Predictions:**
  - R1: human-vs-human deck-outs down at least 5 points; pace up at least 0.3 Prizes by turn 20; the walls' verdict down at
    least 0.04, mostly through the lists' seat; ordered by dose; Elo of at least -15.
  - R2: inside |A/A gap| + 2·SE of a difference (about 2.1 points on deck-outs; ±0.035 on the walls, or about 2,300 games
    per pairing), read only if the manipulation check passes and the doses agree.
  - R3: pace up, while the walls' verdict is flat or higher and their deck-out wins keep their Prize leads.
- **Kill rule:** at 10 iterations, stop only if the training ending mix and the training win margin are both inside the A/A
  arms' range; otherwise run to 20 before reading the panels. Stop at once if Elo falls below -40.
- **Distinct from:** H29 (margin only in the draft reward); H52; H53; H54 (potential-based shaping telescopes at gamma 1);
  remedy (b) of H45 and H46.
- **Cost:** 1 h of code, 1-2 h for the testbed, 2 slot-hours and 1.5 GPU-hours. It does not count on H77's step 2.

### H105 · N2, N10 · untested · Branch starts from the pilot's own games: exploring starts and a reverse curriculum over decisive prize-race positions

- **C id:** C36, intervention. **Plan:** parked. It takes 2-3 days of code, needs the testbed and H79's line-scored puzzles,
  and runs only if H104 and H79 point to competence (R2).
- **Rivals:**
  - R1 coverage;
  - R2 variance;
  - R3 representation or learning rule;
  - "learned there but no transfer", added.
- **Design:**
  - **Code:**
    - a neutral re-deal clone (each player's deck and Prizes reshuffled together, hands kept);
    - ring-buffer capture and post-game selection;
    - a per-worker branch pool in the rollout worker that `rl/train.py` uses. It is capped at a few thousand states,
      replays a share of older starts against forgetting (as Florensa does), and logs pool statistics;
    - branch-group ids through rec, packRollout and rollouts.py;
    - the first-decision RLOO override in `advantages()`, keyed per seat: only the deciding seat's first decision gets the
      leave-one-out advantage;
    - re-deal invariance tests.
  - **Testbed:** H77's (time an iteration first).
  - **Arms:**
    - A: the control, in 2 seeds, shared with H104;
    - B: 50% branch starts, K = 1;
    - C: K = 4 with the vine baseline, matched to B on the number of distinct branch states (4 times B's branch-game share,
      or a K = 1 arm at C's state count).

    At least two seeds of B and C, with the bar set from the spread across seeds (or B and C pooled against control for R1,
    with C vs B secondary). Arm D (Dominion engine starts) is split off or dropped.
  - **Dose and coverage readout:** each iteration, the share of branch states (and of control states at turn 8 or later)
    where a win-this-turn line exists, or PlusPower, Gust or Energy Removal is in hand. If PlusPower coverage is near 0, add
    Trainer-rich wide decks to the pool or drop the PlusPower prediction.
  - **On-distribution positive control:** held-out branch states from games no arm trained on, played out with common random
    numbers by each arm's pilot against the control pilot.
- **Predictions:**
  - R1: B and C beat A, with C about equal to B (a numeric threshold for "C beats B" is stated): PlusPower-only up at least
    0.10 and Trainer-first up at least 0.05 (line-scored); deck-outs down at least 3; pace up at least 0.3.
  - R2: C beats B, while B is about equal to A.
  - Held-out branch states: learned and transferred (R1 or R2); learned, but puzzles flat (no transfer); or not learned (R3,
    or too low a dose).
- **Kill rule:** at 10 iterations, kill only if the branch arms fail the held-out branch-state test (no gain beyond the seed
  spread), or on the Elo guard (below -30) or the Brier guard (more than 10% worse). Puzzles and tempo are read at 20.
- **Distinct from:** H17, H16 and H11; H08's untested "variance-reduced advantages".
- **Cost:** 2-3 days of code, plus H77's testbed (about half a day) and H79's puzzles (about 4 h).

### H106 · N2, N10 · untested · Expert iteration v4: soft, gated, CRN-paired search targets with a frozen leaf value

- **C id:** C37, intervention. **Plan:** parked. It takes 1.5-2 days, and it is gated on H72's CRN self-agreement of at least
  0.80 and on H79, H80 and H81.
- **Scope:** Gumbel top-k option sampling (part of #144's v4) is not included, so a null does not close the whole v4 family.
  R2's conclusion is scoped to this target family.
- **Rivals:**
  - R1 target quality;
  - R2 not transferable: no absorption at a dose that measurably moves the policy;
  - "absorbed but puzzles flat", which falsifies v4's targets rather than transferability;
  - R3 style without strength.
- **Design:**
  - **Testbed:** a fork of resetcap 499 on H77's testbed (built here or depended on). The control is shared with H104. v4
    runs 3 segments of 10 iterations.
  - **Probes:** capped at 2 per game (about 1,000 probes an iteration), with a 1-iteration smoke to time it first. Each
    probe runs CRN tsearch over at most 8 options × 4 shared worlds, at horizon 1.
  - **Leaf:** lines are played by the frozen snapshot with its own value, so the leaf's player and value are consistent; or
    by H81's V_eval. The pilot-v2 initialisation the snapshot inherits is accepted, not avoided.
  - **Targets:** π_t ∝ π·exp(clip(A/τ)), with τ the median per-probe advantage SE and the clip pre-registered.
  - **Gate, symmetric:** a probe is kept when the spread between the best option and the runner-up (or any significant
    advantage) passes, including probes where search confirms the chosen move.
  - **False-pass control:** split worlds (pick the best on 2 CRN worlds, confirm it against the chosen move on 2 fresh
    ones), or a pooled per-class variance with Bonferroni over options. The pass rate is reported on a null of two
    independent CRN evaluations of the same options (H72's data).
  - **Loss:** KL(π_t ‖ π) at weight 0.05, over all rows; a second dose of 0.15 if a slot is free.
  - **Absorption readout:** KL(π_t ‖ π) and target agreement on held-out probes, against the control.
  - **Engineering:** a second model slot for the frozen leaf; per-line score return; storage for soft targets and KL; tests
    (identity at weight 0; KL equals cross-entropy for one-hot targets).
- **Predictions:**
  - R1: Trainer-first up at least 0.05 and PlusPower-only up at least 0.10 (line-scored); deck-outs down at least 3 and pace
    up at least 0.3, with SEs (2,048 tempo games, or paired deals, so that a 3-point deck-out difference is about 2 SE); Elo
    of at least -10; entropy up at most 0.05.
  - R2: no absorption at a dose that moves the policy, or Elo at most -20.
  - R3: puzzles rise while pace and Elo stay flat.

  Puzzles up with mixed tempo has a mapped outcome.
- **Kill rule:** after segment 1, stop if Elo is below -20 or entropy rose by 0.15. After segment 3, stop if the puzzle
  classes are up less than 0.03.
- **Distinct from:** H11 (every hard-target form is do-not-repeat); H14 and H05.
- **Cost:** 1.5-2 days of code, plus the testbed.

### H107 · N4, N5, N7 · untested · In-loop powered judge screen: all-searched judge, paired pooled search correction, clone-invariant panel

- **C id:** C38, intervention. **Plan:** parked. It is gated on H89 (cycle 2) and H72; arm A is about 15 h of one slot,
  overnight.
- **Rivals:**
  - R-strength-in-loop;
  - R-redundancy-in-loop;
  - R-inert-in-loop;
  - R-pooling-misspecified, used only where arms A and B both run.
- **Design:**
  - **Fork:** from 479 with `--reseed 2`, and scr-t60gate479's flags written in full.
  - **Arm A, all-searched (no new code), kept in every gate branch as the power reference:**
    - `--judge-search 1600`, so every unrecorded game is searched; `judged()` then returns the searched mean, and
      `--select-z` uses its SE;
    - a small greedy replay of the same deals (about 200 an iteration), so flips can be counted against `null_searched`.
      Otherwise A's readout is composition-only;
    - k4 d2 (with CRN only if H72 validated it) or more search workers;
    - iteration time: about 42-48 min, from #148's 319 s per 200 searched games. The first iteration is measured, and the
      time kill is about 60 min.
  - **Arm B:**
    - 300 searched games an iteration, each also replayed greedily;
    - a ridge fit of searched minus greedy outcomes on game-agnostic features from the engine's card supertype only:
      creature/Pokémon, non-creature spell/Trainer, land/Energy, and basic vs special if the engine marks it. There is no
      evolution split;
    - a held-out check: the corrected score must predict the next iteration's searched outcomes better than the greedy
      mean (paired log-loss or Brier), beside the permuted-feature null. B is closed if w fits out of sample no better than
      its permuted null;
    - time kill about 15 min.
  - **Arm P:** about 1 day of code plus H89's builder, with a paired-difference `--select-z` test.
  - **Control:** the t60gate479/jsearch479 near-A/A pair, and H98's band once it is available.
  - **Replication:** any arm that passes gets a second reseed before adoption.
- **Predictions (rewritten for whichever arms a gate branch runs):**
  - R-strength: A and B over 485-499 give a mean acc ΔPokémon of at most +0.5 and ΔTrainers of at least 0 per accepted move
    (the control: +1.2 to +3.1 Pokémon and -0.6 to -2.9 Trainers a move from 488), and at most 58 decks holding both walls
    at 494 (the control: 70 and 76).
  - R-redundancy: P moves while A and B stay in the control band.
  - R-inert: every arm stays in the control band.
  - R-pooling-misspecified: A and B differ by at least 12 decks at 494 (twice the pair's spread), or by the share of
    selection decisions on comparable decks where B's corrected choice differs from A's searched choice.
- **Kill rule:**
  - At 489, stop an arm with at least 58 decks holding both and a mean acc ΔPokémon of at least +1.0 over 485-489.
  - The time kills above.
  - Stop P if more than 40 decks move an iteration for 3 iterations.
- **Distinct from:** H23 (`scr-jsearch479` is do-not-repeat); H20, H39 and H40. B's correction is a deck-shape linear model
  (H69's do-not-repeat class), separated from it only by the paired search-minus-greedy residual target.
- **Evan:** adopting B, a meta-level hand-designed model, needs his approval (rule 3).
- **Cost:** A takes 8-14 h of one slot; B about 1 day of code; P about 1 day.

### H108 · N4, N8 · untested · Reset-and-fine-tune judge in the loop (Strgar and Kriegman's few-shot regime), with a zero-shot arm

- **C id:** C39, intervention. **Plan:** parked. It needs a P0 and Evan's ruling on the pilot-v2 lineage, and about a day of
  code. N3 is dropped from its nodes.
- **Evan:** it extends his row 5 (practise each deck before it counts) from the shared pilot to the judge. P0 defaults to
  the human-free full-pool pilot (H99's W) unless he explicitly accepts the pilot-v2 lineage (H86's W1). The ruling goes in
  `notes/evan-requests.md`. With pilot-v2 as P0, the zero-shot arm would be an H20 do-not-repeat variant changing only the
  judge share.
- **Rivals:** R-accumulation, R-fast-learner, R-P0-bias.
- **Design:**
  - **Gate:** H86 returns H-reset-viable or H-slow-accumulation. W's strength is checked (puzzles, JF1, JF2) before it serves
    as P0, and its cost is reconciled with H99's estimate.
  - **Refresh:** every R = 5 iterations, P0 is loaded into slot 1 with a fresh Adam. It fine-tunes on F = 1,000 games among
    the current population, with equal games per k-means cluster and the current candidate draws (offspring) included. (Or
    R = 1 and F = 500.) Slot 1 then plays every unrecorded game, greedy. The judge network and its Adam are checkpointed.
  - **Arms:** reset and zero-shot. An optional third screen runs a reset arm with frequency-weighted fine-tune games, which
    separates the reset from cluster balancing; without it, a positive result credits the two jointly.
  - **Judge probe:** the per-refresh 1,152-game walls probe runs outside the loop on a saved judge checkpoint (otherwise the
    overhead is about 20-25%).
  - **Flags:** written out in full.
- **Predictions:**
  - R-accumulation: the reset arm has at most 55 decks holding both walls at 494 (the control: 70-76), an acc ΔPokémon of at
    most +0.5, and a judge verdict on the walls of at most 0.5 after each refresh.
  - R-fast-learner: at least 65 by 494, and the judge back to at least 0.6 within one refresh.
  - Zero-shot arm: R-fast-learner predicts that it holds (at most 55) while the reset arm relapses (at least 65).
    R-accumulation predicts that both hold unless P0-bias fires.
  - R-P0-bias: median Pokémon of at least 20, or deck-outs of at least 50%, for 3 iterations.

  A count of 56-64 at 494 is inconclusive, and gets a `--reseed` replicate.
- **Kill rule:**
  - At 489, stop only if at least 64 decks hold both, or at least 58 with a mean acc ΔPokémon of at least +1.0 over
    485-489.
  - Stop the reset arm if its judge exceeds 0.65 after two refreshes.
  - The P0-bias stops above.
- **Distinct from:** H20 (`scr-v2` and `scr-judge2` ran the zero-shot arm with pilot-v2); H16; H43; H34.
- **Cost:** about 1 day of code; +10-15% per iteration; 2 screens × 20 iterations.

### H109 · N9, N6, N12 · untested · Evan's ruling on the Stage 3 bootstrap components: a kind-aware base measure, a pilot-first warm-up, and the deck generator

- **C id:** C40, decision for Evan. **Plan:** item 4, in the same message as H102 (about 10 min of his time).
- **Evan:** a decision for him, protecting rules 1-2 before Stage 3 spends compute.
- **Rivals:** R-allowed vs R-prior.
- **Questions, with every hand-set constant disclosed:**
  - **Q1, base measure:** may the head's incoming draw start from a kind-aware base measure? Same type as the outgoing card
    with probability 0.8, type-balanced otherwise. The type partition is named, and the 0.8/0.2 constants are hand-set. The
    type-balanced share drifts composition toward equal thirds: about -0.16 Trainers and +0.13 Pokémon per 6-swap draw from
    the human median.
  - **Q2, warm-up:** may Stage 3 train the pilot first, with a stop criterion? The proposed criterion (at least 70% of games
    ending by Prizes or no Pokémon) singles out some of the game's own win conditions, deck-out being one of them. A
    game-agnostic alternative is offered: the share of games won with a positive end-score margin, or a fixed lead over a
    random-init pilot.
  - **Q3, generator:** `wide_deck` vs the flat `random_deck`. `wide_deck` uses Energy U[8,34], 1-4 lines, Stage 1 lines 60%,
    Stage 2 50%, and 75% matching Energy, for a median start of 8/29/20+2. `random_deck`'s Dirichlet mean is about
    20/20/20; the human median is 13.5/28/18. `random_deck` carries to MTG in form (a Dirichlet split over the game's card
    types under its legality rules). `wide_deck`'s evolution-line structure has no MTG analogue.

  The evidence is already in the log, so the questions are asked now, not after H92 and H99: a uniform draw over this pool
  is 81% Pokémon and 2% basic Energy (#124, H27); a plain-result pilot fell from 92% to 7% deck-outs by iteration 24 on
  fixed decks (#71); #63.
- **Predictions:** a Stage 3 action is written for every answer, conditional yeses included ("yes if the constants are
  learned or derived").
  - R-allowed: H110's kind-aware warm-pilot cells become method candidates.
  - R-prior: they stay diagnostics. Stage 3 uses H110's Nf base measure (or uniform over clusters of W's card embeddings),
    and W retrains on flat decks.
- **Kill rule:** with no answer within a day, H110 runs as a diagnostic at the game-agnostic level.
- **Distinct from:** #51 and the 10-09 rule settled only human lists, bots and the deck-out-0 reward. No ruling exists on
  kind-aware proposals or the generator. Relevant families: H27, H45.

### H110 · N9, N6, N8 · untested · Proposal base measure from scratch: a factorial of base measure × pilot start × start decks

- **C id:** C41, intervention. **Plan:** parked. It needs H109's ruling, H99's W and H92; cycle 2, or the one-day fallback
  diagnostic.
- **Rivals:** R1 arrival, R2 bootstrap, R1×R2, R3 results-driven, R-generator.
- **Design:**
  - **Base measure in `rl/draft.py`:** a fixed offset b0 = log q0(c | j) on the head's incoming logits. The floor tempers
    toward q0 (`floor_temperature` rewritten for base-measure tempering), `--draft-ent` becomes -KL(π ‖ q0), and log-probs
    stay exact.
  - **Factor A, the base measure:**
    - U: uniform over cards (today's head);
    - Nk: kind-aware and exactly neutral. Its 0.2 branch draws a kind in proportion to the deck's current kind shares, so
      that under the copy-uniform cut the expected incoming shares equal the outgoing ones. (Or the 20/20/20 fixed point is
      stated with its predicted drift per cell.);
    - Nf: q0 ∝ exp(cos(f_c, f_j)/τ) over the pilot's card features, with τ set so q0's mean entropy is 3 nats, and q0
      cached per view under a learning pilot. The MiniLM text prior is flagged.
  - **Offline audit (`op_audit.py`, written for this):** Nk within ±0.1 Pokémon and Trainers a draw; Nf within ±0.15. This
    keeps cumulative null drift under about 2 cards over 30 iterations.
  - **Factors B and C:** B is the pilot start, random init (R) vs W; C is the start decks, wide vs flat.
  - **Cells:**
    - Nk.R.wide;
    - Nf.R.wide, on scr-scratch's exact recipe;
    - U.W.wide;
    - Nk.W.wide, in two seeds;
    - U.W.flat and Nk.W.flat;
    - the anchor Nk.frozen-pilot-v2, read against scr-v2;
    - Nf.W, if Evan rules out kind labels;
    - Fq, which is H100's seeded-field arm.

    U.R.wide is not rerun (H45/H46 do-not-repeat).
  - **Controls for the R cells:** Nk.R.wide runs on scr-scratch's config like Nf.R.wide, or a short matched U control
    (about 5 iterations, about 20 min) runs as a control. Also replay scr-scratch's config for 2 iterations on current code,
    to confirm it reproduces its initial deck-out share and Pokémon rise, stating the count-feature setting.
- **Predictions:** the candidate's bands. For example:
  - R1: U cells gain at least 10 median Pokémon by iteration 10, while neutral cells stay within ±3 with |acc - prop| at
    most 0.3 a move.
  - R2: Nk.R.wide stays at 80% or more deck-outs.
  - R-generator: Nk.W.flat does not find the human shape from flat starts.
- **Kill rule:**
  - The R cells are exempt from the deck-out kills and from the extension's deck-out stop, and both run to 30
    unconditionally, since R1 vs R1×R2 vs R2 is read there. They keep only the composition kill (median Pokémon of at
    least 35), or a deck-out kill calibrated to #71's curve (stop only if deck-outs at iteration 20 or later exceed #71's
    matched-iteration value by more than 20 points).
  - Other cells: as in the candidate (never before iteration 4; median Pokémon of at least 35 or deck-outs of at least 90%
    for 2 iterations).
- **Distinct from:** H27, H31, H32 and H34 (the amount of flattening, never its target); H45 and H46.
- **Cost:** 0.75-1 day of code. Machine time is about 4.5 slot-hours, plus 0.4 h for the anchor and about 2.6 slot-hours for
  the R cells' 30-iteration runs. The W cells depend on H99.
- **Evan:** whether Nk and the wide generator may enter the method is his ruling (H109). Until then those cells are
  diagnostics.

### H111 · N6 · untested · Best-of-K credit: train the draft head for the selection it serves (winner-only credit, distinct starts)

- **C id:** C42, intervention. **Plan:** parked. It depends on H93; its random-one control runs on H93's bench in stage 2 if
  drift is found.
- **Rivals:**
  - H-objective-mismatch;
  - H-preference;
  - dilution, added: less signal, so a slower head.
- **Design:**
  - **Gate:** H93 must find the collapse signal-driven.
  - **Information-matched control:** random-one credit. One uniformly chosen candidate per deck gets the same capped
    magnitude distribution, and zero when the incumbent would have won. It runs at least on H93's bench, under null and
    planted δ* rewards, beside winner-only and mean credit; in the loop too if a slot is free.
  - **Separating the two factors:** the primary in-loop arm is winner-only credit with the current i.i.d. sampler (or the
    2 × 2 of credit × distinct starts runs on the bench first). The first-incoming-card uniqueness readout is not evidence
    for the credit hypothesis in any arm that uses Gumbel-top-k first cuts.
  - **In the loop:** `rl/metagame.py` step 4 with `--select --candidates 3` and no gate (the ctl479 recipe). The winner gets
    (s_win - s_second)/SE, capped at 3; every other draw gets 0. Fork 479, `--reseed 2`, 20 iterations; control
    scr-ctl479.
  - **Engineering:** the first-event exclusion flag is stored in the sample dict, so resumed seasons replay log-probs
    correctly. A unit test checks that the incumbent-wins case gives an exactly zero head gradient.
  - **Secondary ground-truth readout:** the best decks' P/T/E and their distance to the human medians. A head that stays
    undecided but keeps adding Energy is not progress.
- **Predictions:**
  - H-objective-mismatch: winner-only beats random-one on h_in under planted signal. Dilution predicts they are equal.
  - In the loop: adopt or advance only if the h_in gap over the control is more than twice the A/A RMS (0.38) at both 492
    and 499, and the wall cluster is at most 70 at 499. An h_in of 1.0-2.0 at 492 gets a second reseed. The A/A spread of
    prop's composition (ctl479 vs resetcap, 480-499) is computed before the 0.3-card bar is used.
  - H-preference: h_in at most 1.0 by 494, and the wall cluster at least 75 at 499.
- **Kill rule:** only if h_in is below the control's by more than 0.4 nats (the A/A RMS) for 3 consecutive iterations, and
  not before about 486; or if the wall cluster reaches 75 by 494.
- **Distinct from:** H30-H34; H37 and H38; H25 (acceptance, not credit).
- **Cost:** 4-5 h of code, including the random-one arm and the bench hooks; one slot for about 2 h.
- **Evan:** if it works, the next arm is winner-takes-all credit over his 3 heads.

### H112 · N7, N6 · untested · Wall-free island in Evan's league of 3 heads: is the wall attractor absolute, or does it depend on the field?

- **C id:** C43, intervention. **Plan:** parked. It takes 1-1.5 days. Under J1 the walls are a Condorcet winner, so
  `notes/method.md` section 7 reads S and X arms only on mechanism readouts, and H96 predicts a null; it waits for H96 and
  H85.
- **Evan:** completes his league of 3 heads (row 12, approved 2026-10-20) in its untested form. If adopted beyond diagnosis,
  the hand-labelled wall-centroid island assignment is replaced by an automatic or learned niche rule, which needs his
  rule-3 sign-off.
- **Rivals:**
  - H-absolute-attractor. Prior evidence: walls emerged from a non-wall field on the main line by 160 (H44's DATA). This
    test differs: the current pilot, the present non-wall types, and no wall opponents.
  - H-field-dependent.

  A proposal-drift explanation is controlled.
- **Design:**
  - **Fork:** from 479 with `--reseed 2`, using scr-t60gate479's flags without `--type-cap` (stated), plus
    `--draft-heads 3 --draft-heads-init copy`.
  - **Islands:** 33/33/33. W1 and W2 are walls; C is the 25 non-walls plus 8 ten-card mutants of C's best (the dropped decks
    are stated).
  - **Membership:** by core cards (Chansey+Snorlax presence, or Pokémon overlap to the wall core), not whole-list overlap.
    Shared staples put distinct human archetypes at 0.54 overlap. The control's 0.32-0.39 band is recomputed with the same
    definition.
  - **Pairing:** judged games are allocated to islands in proportion to their size, and each head's field samples (views)
    are drawn within its island. Recorded PPO and practice games stay global, which requires separating the judged and
    recorded pairing loops.
  - **Proposal-drift control:** every counted iteration, the overlap change (to the wall core) of accepted minus proposed
    moves in island C, from the acc/prop logging, and/or C with a reset head. Conversion is attributed to the judge only if
    accepted moves exceed proposed ones.
  - **Counting:** lineage-level, separating conversion by accepted moves from mutant descent.
  - **Torus:** the torus arm is dropped.
- **Predictions:**
  - Absolute: C's wall-core decks rise from 0 to at least 13 of 33 by 499, through accepted moves exceeding proposals.
  - Field-dependent: at most 3, with at least 2 clusters of 8 or more decks with their own cores.

  5-10 converted decks is undecided. That triggers a pre-registered extension to 509, with C's per-iteration overlap slope
  compared with the control's accepted-move slope.
- **Kill rule:** stop at 489 if C already holds at least 13 wall-core decks.
- **Distinct from:** H37 (the league paired decks at random across the population); H38; H39 (a global cap); the critic's
  opponent-mix gap.
- **Cost:** 0.5-1 day of code; one slot for about 2 h.

### H113 · N7, N5 · untested · Hard selection-time type cap on a descriptor that sees the walls: label or substance?

- **C id:** C44, intervention. **Plan:** parked. It is gated on H112, and its thresholds needed normalising first (done
  below).
- **Evan:** a hard cap is a hand-built population rule. It needs his rule-3 sign-off before adoption (plan section 4, item
  10).
- **Rivals:** H-leak vs H-convergent.
- **Design:**
  - **Code location:** `descriptor.py` and `boundary.py` move from the other session's scratchpad into the repo. One shared
    overlap implementation serves both the cap and the readout (founder membership or 479-centroid overlap for both, or the
    two side by side).
  - **Descriptor:** the copy-weighted overlap of copy-limited cards; greedy founders at link 0.5.
  - **The cap:** 49 decks, enforced by `--select` refusing any move into a cluster at or over the cap. Turnover entrants and
    the fork's 24 mutants are subject to the same cap (redrawn or refused, and logged). A cluster that goes over the cap
    through founder recomputation between turnovers is handled by a stated rule and logged each iteration.
  - **Control's turnover mix kept:** MUTANT_SHARE 0.25, wide entrants, protect 20, except for removing the over-cap excess.
    So the hard cap is the only factor changed against scr-t60gate479. (Or MUTANT_SHARE 1 and unprotected removal are
    declared as separate factors.)
  - **Baselines:** the band, mean overlap and cluster count are measured at 480, right after the fork replacement, and the
    predictions are stated as changes from that baseline. Band and overlap are expressed as fractions of the non-walls,
    outside the control's normalised 479-498 range (a band fraction up to about 0.77).
  - **Refused-move thresholds:** calibrated on the control's base rate of non-wall moves into the wall cluster (about 0.6 an
    iteration in scr-t60gate479, so about 1-2 with 50 non-walls; computed with `lineage.py` on every snapshot). Only moves
    across clusters count.
  - **Substance readout:** the non-wall clusters' share of wall-core cards, and their Energy and Trainer counts against the
    479 non-walls.
  - **Evaluation:** an absolute score against the 24 lists under pilot-v2 and under the run's pilot, plus the distance to
    the human medians.
- **Predictions:**
  - H-convergent: the band fraction and non-wall overlap rise beyond the control-normalised range; refused cross-cluster
    moves run above the base rate and rise; the wall core arrives in non-wall clusters; at most 1 non-wall cluster of 10 or
    more decks.
  - H-leak: band and overlap at or below the baseline; refused moves near the base rate and falling; at least 2 non-wall
    clusters of 10 or more decks with their own cores (mutual overlap below 0.35).
- **Kill rule:** symmetric. Neither rival is decided before 15 iterations; the refused-move kill is rescaled to the base
  rate.
- **Distinct from:** H39 (the built cap: soft, at turnover only, on the deck_kinds descriptor, refuted as built); H64.
- **Cost:** half a day to a day of code, including the logging (refused cross-cluster moves, cap excess, entrant redraws);
  one slot for about 2 h.

### H114 · N1, N3, N10 · tested (C45, #168): hurts untimed, gains under the rule · The 2000 round rule as the pilot's reward teaches tempo that transfers to the lists

- **Mechanism:** W2 practises games that end by benching out and are paid the same however slowly they are won (#160).
  Under the round rule (Evan's D1, row 41) a win on Prizes at time pays +1/3, a draw −1/3 and a loss −1, so the pilot
  is paid for finishing; the human lists were built for that clock (#139).
- **Test:** C45 (`runs/pilot/C45/record.md`): forks R (`--round-turns 20-45`) and P (none) of W2's iteration-119
  checkpoint to 199, seed 2, looks at 139/159/179/199 untimed and under the rule.
- **Rivals and bands:** tempo (R − P lists Elo at least +50 at 199 and +25 at 179), neutral (|R − P| below 25), hurts
  (at most −50). Judge by-product: R's JF1 share of the event points at most 0.45 and 0.05 below P's.
- **Distinct:** #140-#143 and #148 used plain-draw limits in the metagame loop; C35 (H-margin) pays the Prize margin
  and was not run. New: the event's points as the pilot's reward, read on its competence on the lists.
- **Result (#168):** at 199, R − P on the lists −64.7 Elo untimed (Hurts) and +54.1 under the rule (the timed-play
  band). R plays for a Prize lead at the cut (Prize endings in training 17% → 3-5%), not faster; untimed, the walls
  deck it out. Its event-points JF1 0.528 against P's 0.546 (by-product band not met). P gained 22 Elo in 80 iterations
  while its JF1 rose 0.58 → 0.67 and the walls' deck-out wins 34% → 52%. Do not repeat: the rule alone as reward from
  W2 119 with T 20..45.

### H115 · N3, N9 · stopped by the stall rule (C46, #166) · A learned practice distribution (replay by positive value loss, with card edits) transfers to the lists better than fixed wide decks

- **Mechanism:** W2's practice is fixed hand-built wide decks whose games are mostly bench-outs (#160). Prioritized
  level replay with ACCEL's edits (`rl/curriculum.py`) moves practice toward the decks where the pilot's games beat
  its expectation most.
- **Test:** C46 (`runs/pilot/C46/record.md`): a fork of W2 at 119 to 199, seed 2, against C45-P.
- **Bands:** transfer (lists Elo at least +50 at 199 and +25 at 179 over C45-P), neutral (below 25), hurts (at most
  −50); drift reported (buffer shape, Prize-ending share at least 30%).
- **Distinct:** analysis-2026-10-06 item 3 proposed it and it was never built; #42/#48 and C30 used fixed decks.
- **Result (#166):** stopped at 125 by the stall rule (deck-outs 0.43). Replay moved practice from 74-81% bench-outs to
  Prize races (33-37%) and deck-outs (38-55%), with games twice as long, and the buffer median from 8 / 28 / 24 to
  13 / 28 / 17 in 5 iterations (human medians 13.5 / 28 / 18; nothing in it reads a deck's shape). Transfer unread.
  Open variant: with the round rule (C48).

### H116 · N1, N4, N5 · tested, 2 seeds (C47, #167, #170, #173): shape replicates, type split · The 2000 round rule in every game of the loop breaks the wall type

- **Mechanism:** the walls win late by deck-out (median 56-61 turns); under the rule (Evan's D1, row 41; T 20-45 per
  C02's R-unknown) those games are cut and decided on Prizes, a slow win pays 2/3 of a point and a Prize tie 1/3 each.
- **Test:** C47 (`runs/screens/C47-record.md`): `scr-gate479`'s recipe from 479 with `--round-turns 20-45`, reseed 5,
  against the three gate seeds of #153.
- **Bands:** type (wall-core decks at most 58 at 494 and 499), shape only, none. Prior: none or shape only (C13's
  greedy W(J1, Π) 0.54-0.56).
- **Distinct:** #140-#143 and #148 used plain-draw limits.
- **Result (#167, #170, #173):** window distance 6.27 / 6.77 against the gated 9.55-11.70 (Welch +4.10 [+1.75, +6.45]);
  wall-core 53 / 47 / 57 / 69 (seed 5, Shape only) and 47 / 44 / 51 / 53 (seed 6, Type), pooled +12.7 [−7.0, +32.4]
  fewer than gated. Seed 5's pilot: level with pilot-v2 on the lists under the rule (+1.6 [−16, +19]); walls' event
  share 0.504 under the rule, 0.668 untimed. Open: a third seed; the rule plus a searched or distilled judge.

### H117 · N3, N1, N10 · stopped (C48, #169): practice collapsed to bench-outs · The learned curriculum under the round rule transfers to the lists better than the rule alone

- **Mechanism:** #166's curriculum found human-shaped decks and Prize races but, untimed, long games ended by deck-out;
  under the rule no game passes T.
- **Test:** C48 (`runs/pilot/C48/record.md`) against C45-R and C45-P.
- **Bands:** transfer (+50 at 199 and +25 at 179 over C45-R under the rule, untimed no worse than −25 against C45-P),
  neutral, hurts; stall kill at 0.30 deck-outs.
- **Result (#169, #171):** stopped at 149 by hand (practice 95% bench-outs). At 139: −5 under the rule and +54 untimed
  against C45-R; walls' event share 0.611. The positive value loss scales with the reward, and the rule's ±1/3 time
  results make early bench-outs score highest. Do not repeat: the unnormalised score under the rule.

### H118 · N2, N10, N1 · testing (C49, #169) · Soft, CRN-paired search targets at a moderate all-rows dose move search's play into the pilot

- **Mechanism:** one-turn search gains 0.16-0.17 on the lists' seat (#156, #159); hard targets failed (#103-#106).
- **Test:** C49 (`runs/pilot/C49/record.md`): C45-R's command plus `--search-distill 20 --probe-p 0.05`, against C45-R.
- **Bands:** absorb (+50 at 199 and +25 at 179 under the rule), not transferable (at most −20), style only (agreement
  up 0.10, Elo within ±25). Kill: entropy 0.15 above C45-R's.
- **Distinct:** H11's hard-target runs; C37's frozen leaf is not built (the live pilot's value scores the lines).

## 7. The queue (first cycle, the cheaper spend Evan chose)

This is the portfolio of `notes/plan-cycle1.md`, in its order, with the bands and kill rules of section 6. Tier A (items 1-10) costs
about 35 dh over about 1.5 days elapsed. Tier B (items 11-14) costs about 29 dh and may spill into cycle 2. The conditional
items (15-16) cost about 18 dh and run only if their gates fire. dh means desktop-hours: a screen slot-hour counts 1, a
GPU probe-hour 0.5, a CPU probe-hour 0.25 and an agent-hour 1. The agent lane is the bottleneck, not the GPU.

**Machine limits:**
- at most 3 screens, each about 2.7 GB RAM and 3.5 GB GPU;
- a GPU probe (RL_GPU_SHARE about 0.15) only beside at most 2 screens;
- one CPU probe (4 workers) beside them;
- H72's searched path only while at most 2 screens are live;
- engine and runner edits opt-in and default off, landing between screen batches, each checked by a seeded trace hash.

**Step 0, before any launch.** Clear the log debt (plan section 6, items 1-3):
1. Log the exact STS chain (section 2) and then the method and plan.
2. Install `out/method.md` as `notes/method.md` and this file as `notes/hypotheses.md`.
3. Write `runs/screens/scr-t60gate479/STOP`.

Plan section 6 items 4-11 (indexes, recipes, script copies, banners, evaluators) follow in the same session.

| # | C | H | Item | Slot | Cost | Tier |
|---|---|---|---|---|---|---|
| 1 | C09 | H78 | Open decklists, step 1 | GPU probe beside ≤ 2 screens | ≈ 1 dh | A |
| 2 | C07 | H76 | Zero-training judge zoo | GPU probe beside ≤ 2 screens | ≈ 2.5 dh | A |
| 3 | C13 | H82 | Stage 1: exact STS rule on all 24 lists, wall sets B and C, the J2 linchpin replication, the walls-only seat (stage 1 done, #156: E+P replicates on all 24) | CPU probe (4 workers) | ≈ 3 dh | A |
| 4 | C33 + C40 | H102 + H109 | One decision message to Evan | Agent, then Evan | ≈ 1 dh | A |
| 5 | C29 | H98 | A/A of the gate recipe at 479, reseeds 3 and 4 (done, #153: noise band; S36) | 2 screen slots | ≈ 4.5 dh | A |
| 6 | C30 | H99 | Pilot-first warm-up W (the prevention start; both seeds done, #157: bootstrap ok, H5/H1 unread, W2 continued) | 1-2 slots (`rl.train`) | ≈ 6.5 dh | A |
| 7 | C14 | H83 | Draw-seeking check of the turn-limit runs (Evan, rows 24-25) | GPU job counted as 1 slot | ≈ 2.5 dh | A |
| 8 | C02 | H71 | Outside research on the specification | Agent (deep research) | ≈ 5 dh | A |
| 9 | C24 | H93 | Draft-head bench, null vs planted rewards | GPU probe (head only) | ≈ 3.5 dh (+3 for stage 2) | A |
| 10 | C08 | H77 | Attached-Energy count bug, step 1 | GPU probe (forward passes) | ≈ 5 dh | A |
| 11 | C03 | H72 | GPU-served searched probe with CRN | Infrastructure; GPU with ≤ 2 screens | ≈ 8 dh | B |
| 12 | C10 | H79 | Human-field tempo ladder and competence panel | GPU and CPU probes | ≈ 9.5 dh | B |
| 13 | C35 | H104 | Prize margin as the pilot's terminal reward | 1 slot, arms in sequence | ≈ 6 dh | B |
| 14 | C28 | H97 | Valley test, greedy stage | GPU probe | ≈ 5.5 dh | B |
| 15 | C25 | H94 | Frozen and null-reward head forks (gate: H93's null at 1.5-2.5 nats, or unresolved) | 2 slots (+1 for F0r) | ≈ 6 dh | conditional |
| 16 | C17 | H86 | Matched pilot-v2 fine-tunes, wave 1 (gate: H76's arm (b) in exposure, familiarity or 0.40-0.55) | 3 slots | ≈ 12 dh | conditional |

**Schedule by lane:**

| When | Screens | GPU probe | CPU probe | Agent |
|---|---|---|---|---|
| Hour 0 | H98 s3 and s4 | H78, then H76 | H82 stage 1 | step 0; the H78 and H76 scripts |
| Hour ~2 | H99 W1 and W2 | H93 | H82 continues | the H102 + H109 message; H71 launched |
| Hour ~5 | H83 replays (1 slot); H94 if gated (reseed 3) | H77 step 1 | H99's JF1 and head-to-head evals | H83, H77, then H72 |
| Day 2 | H104 arms; H86 if gated (3 slots, no GPU probe meanwhile) | H72 validation; H79 rungs | H79 puzzle generation | H79, H104 |
| Day 3 | H86 seed 2 and W0 if needed | H97 greedy | H79's searched rung (CPU fallback) | H97; log; close the cycle |

**Floor and coverage this cycle:**
- **Prevention start:** H99's W1 and W2 are two of the first four screens.
- **Incumbent lineage:** at most 2 of the 3 slots run it.
- **Every live Q1 rival has a queued test that can demote it:**
  - E: H82, H83, H71;
  - I: H78, H77, and H76's arms;
  - P: H79, H104;
  - J: H76, H99's JF1, H86;
  - S: H93, H98, H94;
  - X: H97.
- **The leader is attacked first:** the leading rival is the E+P conjunction (#147). H82's blind B/C cells and the all-24
  J2 replication attack it first.

**Decisions for Evan in the message (item 4):**
- D1 (a') and (a), the round rule;
- D2, only if D1 is yes;
- D7, the commit go-ahead;
- the engine fixes behind default-off flags;
- H109 Q1-Q3;
- the pilot-v2 lineage as a method component (H86, H108);
- approval of `notes/method.md` and its Judge scorecard row;
- formally retiring the lab main line.

Two more are conditional: hidden opponent lists (only if H78 finds R1), and rule-3 sign-off before adopting islands, a
torus, a hard cap, QRE/Nash allocation, lexicase or H107-B's correction.

**Routing after the cycle:**

| Result | Next |
|---|---|
| H76 payoff | judge work goes to strength plus the cut (H82 stage 2, H89, H107); H108 closes |
| H76 exposure or familiarity | H86, then H108 |
| H77 or H78 under R1 | a fix before any further judge result builds on the inputs |
| H79 R1 | H106, H107 |
| H79 R2 | H104, H105, H81 |
| H93 signal | head work stops |
| H93 drift | stage 2 fixes and H111 |
| H97 valley | any judge fix needs archetype-scale moves |
| H104 R1 | a second seed, then adoption into R1 |
| H99 ok | W becomes Stage 3's bootstrap and H108's P0 |

**Parked:** none failed review. Each is parked for cost, a missing prerequisite or a dependency on Evan.

| C | H | Why parked |
|---|---|---|
| C01 | H70 | Its measurement half is done (the exact STS chain). Build the engine option (2-3 h) the day a consumer is scheduled or Evan answers D1 |
| C04 | H73 | The registry is hand-written this cycle; launcher enforcement can wait; revisit if H98 shows the gate is real |
| C05 | H74 | Belongs to the first periodic review; needs the SNR-vs-A/A redesign |
| C06 | H75 | Low prior; its fixes are submodule edits awaiting Evan |
| C11 | H80 | Needs H79's line-scored puzzles and exact prompt scoring |
| C12 | H81 | Needs H72's searched path and a per-decision logger; cycle 2 if a searched plateau remains |
| C15 | H84 | Needs H70's runner trace, a per-game dump and an offline pick/rloo replica (about 5-7 h) |
| C16 | H85 | Stage 1 in cycle 2 after H76 names the judges; stage 2 needs H72 |
| C18 | H87 | Subordinate to H76's payoff/exposure split |
| C19 | H88 | Its verdict needs W (H99) |
| C20 | H89 | Needs H72's pass-through and H95's builder; it gates H107 |
| C21 | H90 | Needs H85's matrices and H86's independent-network judges |
| C22 | H91 | About a day of engineering plus 1-1.5 GPU-days; prior lowered by #134-#138 |
| C23 | H92 | Its consumer H110 waits on H109 and H99; run before H110 |
| C26 | H95 | Shares the aligned builder with H89; cycle 2 after H72 |
| C27 | H96 | Its J1 arm is a positive control; its consumers are parked; after H85 stage 1 |
| C31 | H100 | The offline fixed point (H85) goes first; cycle 2 after H85 stage 1 and H99 |
| C32 | H101 | 3-4 days of code; prerequisites H93, H95 and H85 unmet |
| C34 | H103 | Needs Evan's approval of the rule in training and of T's source, plus H70, H79 and H82 |
| C36 | H105 | 2-3 days of code; needs the testbed and H79's puzzles; runs if H104 and H79 point to competence |
| C37 | H106 | Gated on H72's CRN self-agreement of at least 0.80, and on H79, H80 and H81 |
| C38 | H107 | Gated on H89 and H72 |
| C39 | H108 | Needs a P0 and Evan's ruling on the pilot-v2 lineage |
| C41 | H110 | Needs H109's ruling, H99's W and H92 |
| C42 | H111 | Depends on H93; its control runs on H93's bench |
| C43 | H112 | Under J1 the walls are a Condorcet winner; waits for H96 and H85 |
| C44 | H113 | Gated on H112 |
