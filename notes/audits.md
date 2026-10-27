# Audits of the other agent

Evan, 2026-10-24 17:08: "audit the other agent for whether they are stuck in a local minima with their experiments or
truly trying a new experiment", every 30 minutes. One numbered entry per audit, newest last. The auditor only reports:
it never edits `ar/`, the progress log or runs. Each entry covers the ar/ 5-minute loop (`ar/results.tsv`) and the
planning session (progress log, `runs/dayplan`, `runs/probe`).

**Core metric (Evan, 17:30): distance to the human lists, not whether a plan was followed.** "Focus on concrete metrics
towards the ground truth of rediscovering human lists ... If the experiments are barely moving the needle, be clear
about that." From A3 on, each audit leads with these numbers:
- **G1, deck shape:** the 12 best decks' mean Pokémon / Trainers / Energy and its L1 distance from 13.5 / 28 / 18
  (`loop.py ground_truth`, last row and mean of 5). Method §3 target: each within 5 of its median.
- **G2, archetypes:** at least 3 (the lists' effective number is 3.6), measured as the walls' share or the largest type.
- **G3:** the best decks score at least 0.5 against the lists under a qualified pilot.
- **Proxy:** ar/ M, the lists against their Energy-filled copies; start 0.474, target above 0.5. It is a proxy, not
  the ground truth.

**Null by default (Evan, 17:40):** "the simplest explanation is typically that a change isn't doing much unless there
is serious reason to believe it did". A change counts as having an effect only if all three hold:
1. **Bigger than measured noise.**
   - ar/ M: the two-seed mean must be at least 0.02 above the start's 0.474. Reruns of one commit differ by 0.007-0.019.
   - G1: the mean-of-5 distance must be at least 3 below its comparison. Seeds of one recipe differ by about 2: C47
     4.9 / 5.7, gate479 10.3 / 10.8 / 12.3.
2. **Holds on a second seed.**
3. **Falsifiable:** the run's record said beforehand what result would count against it, and the result is read
   against that. Calls made after the fact ("trend", "just under the bar", "provisional", a band moved) count as no
   effect.

Anything else is recorded as **null**. Each audit gives the count: effects / nulls / not yet readable.

A1 and A2 judged novelty and the plan. Read their verdicts with that in mind.

## A1 · 2026-10-24 17:15 · covers ar/ rows 1-21, log #236-#240, probes-1 so far

**Verdict:** the ar/ loop is **partly stuck**: it changes a different part of train.py each time, but every result is
inside its own noise, so it is not learning anything. The planning session is **trying new things**: the 17:00 probes
ask why Trainers are underpriced instead of tuning.

**ar/ loop** (17 experiments since 14:53, 0 kept; HEAD 789cf07 "no value clipping" committed, not yet run because
ar/ is paused for probes-1):
1. It does move between parts of train.py: search-distill weight, GAE lambda, entropy, ending weights, practice
   curriculum, frozen-anchor opponents, step size, search breadth, value clip. It is not stuck on one knob.
2. The keep bar is inside the noise. All 3 `confirm`s failed on seed 2 (LAM 0.8: 0.4815 then 0.4750; curriculum:
   0.4829 then 0.4636; frozen anchor: 0.4917 then 0.4723). Seed 2 moved 0.007-0.019 between runs of the same commit,
   while delta is 0.01 (set from a 3-seed A/A sd of 0.0018; #239 lowered the planned 0.03 floor).
3. It reads trends into noise. "ENT 0 +0.008, so try ENT -0.005" gave 0.451. "M rose as lambda fell, so try 0.6" gave
   0.451. Both rested on single-seed gaps smaller than item 2's spread.
4. Every effect clearly outside the noise is negative: SD 0 (-0.02), LAM 1.0 (-0.03), LR x6 (-0.015). Five minutes of
   baseline training moves M by -0.005, and the movability control (practice on the evaluation decks) only reached +0.015.
   At this budget the loop can detect harm, but so far nothing has shown it can detect help.
5. All 17 are tweaks of one recipe (PPO plus search distillation from the frozen C49-sd start). The model and the
   practice decks are untouched. These program.md ideas are still untried: fresh random practice decks, a value-only
   first iteration, `slot_bind`, WORKERS 14.

**Planning session** (#236-#240, probes-1 from 17:00; one seed each, not yet logged):
- C68 / X1: answering the pilot's own Trainer prompts at random changes nothing (three-group diff +0.002 +- 0.009,
  6,080 games a variant, band "untrained"). The pilot's choices *inside* Trainers are no better than random.
- C71 / X10: permuting the 42 Trainers' identities costs 70 Elo head to head (0.401 +- 0.013, 1,536 games). Permuting
  Energy costs 23 Elo, but the probe's own call is "identity-reading (the Energy control did not bite: check the
  copies)". The pilot does read which Trainer it holds.
- These are new mechanistic questions, not reruns. Together they point at a specific cause: the pilot knows which
  Trainer it has but has not learned to use it. ar/'s ENT 0 idea (row 8) was the only one aimed at those prompts.
- Main line unchanged: the last screens' best decks run 17-20 Pokémon / 17-21 Trainers / 20-22 Energy against the human
  13.5 / 28 / 18 (#237, #238).

**Flags for Evan (not acted on):**
- Raise ar/'s delta back toward 0.02-0.03, or require two seeds before a gap counts as a trend. Right now about 1 run in
  6 is a confirm that fails.
- Feed C68's finding (random-quality choices inside Trainer prompts) into `ar/ideas.md` so the loop works on that
  instead of global loss knobs.
- `drive.py` runs as a background task of the planning session (#240 Found). If that session ends, the ar/ loop stops.

## A2 · 2026-10-24 17:17 · covers probes-1 (C68-C71 done 17:13), ar/ session 6

**Verdict:** the probes are still new and pointed. The other two probes agree with X1: under this pilot, the lists'
Trainers are worth about as much as a blank card. ar/ has resumed, but the findings have not reached it yet
(`ar/ideas.md` does not exist, nothing new logged after #240). Its next run is the queued global knob from before the
probes (789cf07, no value clipping). It is too early to call this "ignoring its findings"; check again in A3.

**New probe results** (one seed each, 24 lists, not yet logged):
- C70 / X5 (filler, 6,816 games): the list's score against its copy depends on what replaces its 6 Trainers.
  - Basic Energy: 0.444 +- 0.015.
  - Off-type Energy: 0.484 +- 0.016.
  - Clefairy Doll: 0.506 +- 0.015.
  - Doll minus basic Energy: +0.062 +- 0.010.
  The pilot gains from extra usable Energy, and the lists' Trainers only tie a near-blank Doll.
- C69 / X3 (off-mirror, 9,936 + 1,536 games): the Trainers' deficit is the same against the other 23 lists as in the
  mirror. Off-mirror is -0.040 +- 0.021, mirror -0.039 +- 0.023, difference -0.001 +- 0.015 (band "general",
  provisional). So M's mirror setup is not what hides the Trainers' value.

**Loops:** alive. drive.py (session 6 started 17:14) and dayplan.py (waiting for probes-2 at 23:30) are both running;
no PAUSE or STOP.

**Flag for Evan:** X1, X5 and X3 now say the same thing: the pilot's Trainer play is no better than random or a blank.
If ar/ goes back to global loss and step knobs, it is likely to repeat rows 5-21. A2 adds no other flags.

**Correction (17:20):** `ar/ideas.md` was written at 17:15:49, just after A2's check, and log #241 records all four
probes. The planning session did feed the findings in. Its 6 ideas target prompt decisions: weighting the policy loss
at prompt rows, turn-level credit, prompt-only entropy, separate advantage normalisation, a value-only first iteration,
and a prompt-heavy practice draw. All use structural features, not card kinds. ar/ session 6 started at 17:14, before
the file existed, so the session that reads it first may be a later one. A3 checks whether the next commits test these
ideas.

## A3 · 2026-10-24 17:35 · ground-truth baseline (all 42 scored screens, `loop.py ground_truth`)

**Verdict: the needle has not moved since 10-23 01:00.** The closest any run has come to the human lists is still C47
under the round rule (10-23, #167). In the day and a half since, 12 screens finished (10-24), and every one is further
from the lists. Every one also runs short of Trainers, which is the deviation the ground truth flags. The 17
ar/ experiments and the 4 probes have not changed a ground-truth number. The probes were never meant to; ar/
has not moved its proxy beyond noise.

**G1, deck shape** (best-12 P / T / E; distance last row, mean of 5; one seed unless noted):
| | P / T / E | distance | mean of 5 |
|---|---|---|---|
| human target | 13.5 / 28 / 18 | 0 | |
| best ever: C47 `scr-round479` (10-23) | 12.2 / 28.1 / 19.8 | **3.2** | 4.9 |
| C47 replication `-s6` (10-23) | 13.2 / 26.0 / 20.8 | 5.2 | 5.7 |
| best since: C52 `h110.nf-c49sd199-s3` (10-24) | 13.8 / 24.7 / 21.6 | 7.2 | 9.7 |
| latest 3: C63 nfR, C63 ctl, C66 (10-24) | 17-20 / 17.5-21.2 / 19.8-22.2 | 14.0-21.5 | 10.7-17.8 |

- Trainers in all 12 screens from 10-24: 14.6-24.7, median about 21, against 28. All 12 are short, by 3.3-13.4 cards.
- Only the two C47 seeds meet G1's "within 5 of each median".
- Comparability caveat: the 10-24 screens are short (1-59 iterations) from pilot starts. C47 ran 20 iterations on
  from the evolved 479 population, which the exploration floor has barred from further forks since #176. The lab's best
  ground-truth state is one the current method cannot build on.

**G2, archetypes:** C47 fails it. 47-69 of its 99 decks are Chansey / Snorlax walls, and the Type band was not met at
499 (#167). The right shape came with one dominant archetype. No 10-24 screen reported G2 in a form I could compare.

**G3:** C47 seed 6's pilot scored 0.449 against pilot-v2 on the lists under the rule (#178), and seed 5's +1.6 Elo was
level with it. No 10-24 run reports G3.

**Proxy M (ar/):** 17 experiments, 0 kept.
- Single-seed range 0.439-0.492. The best two-seed mean is 0.482 (frozen anchor), against the start's 0.474 and the
  target of 0.5.
- All three changes that looked better fell back on seed 2, so no upward move is above noise.
- X5 (24 lists, 1 seed) puts the gap at 0.444: under the current pilot the lists lose to their own Energy-filled
  copies. That is the ground-truth deviation, measured directly.

**What would count as movement:**
- A screen, not forked from 479, with best-12 distance below 7.2 or Trainers at 24 or more.
- C47's shape together with G2 met.
- An ar/ change whose M two-seed mean reaches 0.5. Its effect on G1 would still need a metagame screen.

## A4 · 2026-10-24 17:58 · ar/ rows 22-26, log #242, no new screens

**Ground truth: nothing moved.** No screen has run since C66 ended at 11:01, so G1-G3 are where A3 left them: best
ever 3.2 (C47), best since 10-23 7.2, all 10-24 screens short of Trainers. None is scheduled before the 12:00 window
on 10-25. Until then the GPU goes to the proxy (ar/ M) and probes, so **no ground-truth number can change for about 18
hours.**

**Count: 0 effects / 5 nulls / 1 not yet readable** (44036e9, ENT_PROMPT 0.04, running).

**Proxy M** (single seed each, 5-minute runs, finished):
| row | change | M | vs start 0.474 |
|---|---|---|---|
| 22 | no value clipping (kept: 2 lines simpler, M within delta/2) | 0.4685 | -0.006 |
| 23 | ideas.md 1: policy loss weighted at prompt answers | 0.4594 | -0.015 |
| 24 | ideas.md 2: lambda 1 within a turn | 0.4666 | -0.007 |
| 25 | Evan's A: `history 1` (the prompt's source card visible) | 0.4613 | -0.013 |
| 26 | Evan's B: history 1 plus 4x policy at prompts | 0.4500 | -0.024 |

- None reaches 0.494, and none was run on a second seed. All five are null.
- The probe-directed ideas (rows 23-26) average 0.459, against 0.467 for the 16 global-knob runs before them (rows
  5-21). That gap is inside noise too: targeting the prompts did no better than tuning knobs.
- Simplest reading of all 22 runs: nothing yet tried in train.py moves M within 5 minutes.
  - A plain 5-minute training run lowers M a little. The A/A baseline gave 0.4701 / 0.4665 / 0.4690 on 3 seeds, all
    below the untrained 0.474.
  - That drift is consistent across seeds but small (-0.006), and every recipe tried sits around it.
- Evan's ideas A and B are among the nulls. Each was one 5-minute run on one seed, which this rule cannot read as
  "tried fully".

**New since A3, not ground truth:**
- Log #242: the research session prices the keep bar at about 1 sd. It pools the 3 failed confirms to sd 0.0115 per
  run (3 df) and needs 6 runs per arm to see +0.015.
- So M can at best detect a gain of about 0.02 per change, while the whole range seen so far is 0.439-0.492.
- Probes C74-C76 are queued for 23:30. No new probe readouts.

**Loops:** alive. drive.py is in session 8 (from 17:37) with fixed.py running; dayplan.py is waiting for 23:30. ar/
sessions 6-8 ran 7-13 minutes each, so short but working.

**Flag for Evan:** the next ground-truth number is about 18 hours away, and the proxy has given 22 nulls. A short G1
screen of the kept train.py would say whether the 5-minute loop relates to deck shape at all. The cheapest version
would be about 30 iterations, like the 10-24 screens.

## A5 · 2026-10-24 19:00 · ar/ rows 27-29, probes C73 and C78, log #244

**Ground truth: G1 did not move, and G3 was measured for the first time this cycle. It is far from the target.**
- C78 (frozen C49-sd pilot on both seats, round rule, 288 pairs, 8 games a pair, 1 seed, finished 18:35) played each
  R1 screen's 12 best decks against the 24 lists.
- Their share of decisive games:
  - C52 s3 at 29: **0.119 +- 0.009**.
  - C63 control at 29: **0.210 +- 0.013**.
  - C63 random-pilot arm: **0.139 +- 0.010**.
- The G3 target is 0.5. The best machine decks lose about 80-90% of decisive games to the human lists.
- C52 s3 has the best shape since 10-23 (G1 7.2) and the weakest score against the lists (0.119). Shape distance
  alone does not show progress toward the lists. G1 can improve while G3 stays at the floor.
- C78's pre-written band "R-gap (both at most 0.35)" is met.
- No new screen; G1 is still best ever 3.2, best since 10-23 7.2.

**Count: 0 effects / 3 nulls / 1 not yet readable** (C78 is a measurement, not a change).
- ar/ M, one seed each, finished:
  - row 27, prompt-only entropy: 0.4760;
  - row 28, separate advantage normalisation: 0.4608;
  - row 29, value-only first iteration: 0.4519.
  None reaches 0.494; all null. The ar/ total is now **21 changes, 0 effects**, and all 6 probe-directed ideas
  (rows 23-29) are among them.
- C73 / X1b, prompt oracle (24 lists, 1 seed, finished 18:34): with lookahead answers at the pilot's own Trainer
  prompts, the lists gain **+0.044 +- 0.008** against their Energy copies (S 0.479 against G 0.435; search group +0.063
  +- 0.013; control ok). That is 5 SE on its pre-written band "partial", but one seed, so not yet readable as an
  effect.
  - Even with oracle answers, the lists still lose to their Energy-filled copies (0.479, under 0.5). On this probe,
    perfect prompt answers would close about half of the Trainer gap, not all of it.

**Loops: the ar/ loop has been dead since 18:09.** The Claude plan hit its session limit (HTTP 429 "usage_limit_reached,
resets 9pm"). drive.py starts a session every 10 minutes and each exits at once (sessions 9-13). It should
recover by itself after 21:00. dayplan.py and loop.py's daemon are alive.

**Flags for Evan:**
- G3 is the weakest ground-truth number: 0.12-0.21 against 0.5. Work aimed at shape (G1) or the proxy (M) does not
  touch it.
- If this session uses the same login, these audits draw on the same plan limit as the ar/ loop.

## A6 · 2026-10-24 19:28 · ar/ row 30, log #245-#247

**Ground truth: nothing moved.** No new screen or G3 measurement since A5. The numbers stand at:
- G1: best ever 3.2; best since 10-23 7.2.
- G3: 0.12-0.21 against 0.5 (C78, 1 seed).

**Count: 0 effects / 1 null / 0 not yet readable.**
- ar/ row 30 (ideas.md 6, practice weighted toward prompt-heavy decks): M **0.4457**, one seed, finished. It is 0.028
  below the start, the lowest since row 7. Null.
- All 6 ideas.md items are now tried: rows 23-24 and 27-30, 6 runs, M 0.446-0.476, 0 effects. Evan's ideas A and B
  (rows 25-26) are also null.
- **ar/ total: 22 changes, 0 effects.**

**Loops:** ar/ was stopped on purpose at 18:59. The planning session wrote `ar/STOP` and `ar/PAUSE` for "deploy
(cleanup, chain head, bug batch); restarted after re-setup", and drive.py ended at 19:06. dayplan.py (probes-2 at
23:30) and loop.py's daemon are alive.
- The deploy changes the code under ar/, so M after the re-setup has a new baseline. Rows 1-30 cannot be compared
  with later rows directly.

**Queued, not results:**
- C79-chain: a 5.5-hour overnight test of a "chain head" pilot.
- C77-signals: two dense training signals at 08:30.
- Both read out on M, the proxy, so neither will produce a G1 or G3 number. The only scheduled ground-truth reading is
  still the 12:00 screen on 10-25.

## A7 · 2026-10-24 21:00 · covers the 19:43, 20:13 and 20:43 slots (the plan's usage limit held them back)

**Ground truth: nothing moved, and nothing ran.** There are no new screens, G3 readings, ar/ rows (still 30), probes
or log entries (last #247). G1 is still best ever 3.2 and best since 10-23 7.2; G3 is still 0.12-0.21.

**Count: 0 effects / 0 nulls / 0 not yet readable.**

**Loops: stalled for 2 hours, not dead.**
- The planning session stopped ar/ at 18:59 for a deploy. It committed the bug batch at 19:05 (753d9c4: 2000
  Confusion, face-down slots, last-Prize promote, Clairvoyance, ...).
- Since then no file in rl/, env/, ar/ or notes/ has changed, ar/ has not been re-set up, and the GPU is at 0%.
  The likely cause is the same plan limit that ended ar/ sessions 9-12. It reset at 21:00.
- dayplan.py and loop.py's daemon are alive.
- The deploy changed the engine's rules. Every G1, G3 and M number up to A6 was measured on the old engine, so
  later readings start a new baseline.

**Flag for Evan:** if the planning session does not resume the deploy and re-set up ar/ before 23:30, dayplan.py will
launch probes-2 on the new engine against bands written for the old one.

## A8 · 2026-10-24 21:28 · nothing new to measure

**Ground truth: nothing moved.** There are no new screens, G3 readings, ar/ rows (still 30), probes or log entries
(last #247).
**Count: 0 / 0 / 0.**
**Loops:** the deploy has resumed since A7. Files in rl/ (draft, metagame, remote, train, tests) and env/ (agents,
remote_worker, runner) changed in the last 35 minutes, and the GPU is at 13%. ar/ is still stopped and not yet re-set
up. dayplan.py is waiting for probes-2 at 23:30.

## A9 · 2026-10-24 21:58 · after the restart at about 21:50 (brief from session 333-81)

**Ground truth: nothing moved.** There are no new screens, G3 readings, ar/ rows (still 30), probes or log entries
(last #247).
- G1: best ever 3.2 (C47, 10-23); best since 10-23 7.2; last screen C66 14.0 (11:01).
- G2: C47's walls 47-69 of 99, not met.
- G3: 0.12-0.21 against 0.5 (C78, 1 seed).
- M: 22 changes, 0 effects (old engine).
**Count: 0 / 0 / 0.** The last ground-truth number was measured almost 11 hours ago (C66 at 11:01).

**What the restart killed:**
- `dayplan.py` is not running. Windows probes-2 (23:30), milestone (07:00 10-25), signals (08:30) and screen (12:00)
  will not fire unless it is restarted. The screen at 12:00 was the only scheduled ground-truth reading.
- The planning and research sessions, and this audit's session (the cron job `ef0fd997` survived in the resumed
  session, so it was not re-created).
- Already stopped before the restart, so not lost: `ar/drive.py` (STOP since 18:59).
- Alive: loop.py's daemon (the scheduled task). GPU at 2%.

**Deploy state (git and files):**
- Committed:
  - 753d9c4 (19:05): the bug batch, engine rule fixes.
  - 3d254d5 (21:21): X1b's worker.
  - 1dc02c2 (21:28): dead-code cleanup, stage 2.
- **Not committed:** 20 files, +1,054 / -67 lines. Mostly env/ (tokens.js, game.js, env.js, remote_worker.js,
  tools/test_env.js +274) and rl/ (token_model.py +52, tests.py +160, remote.py, train.py, metagame.py,
  gpu_matrix.py, warmstart.py), last touched 21:40-21:43.
  - This looks like the in-progress card-token and chain-head work (#246, Evan's rows 65-67).
  - Whether its tests pass is **unknown**: the session died before any log entry about it.
- **ar/ is not re-set up:** state.json and results.tsv date from 19:04, the frozen hashes are the pre-deploy ones,
  and HEAD is still 789cf07. With env/ and rl/ changed, `fixed.py` should refuse to run (frozen files changed) until
  `--setup` and `--calibrate`.
- Every G1, G3 and M number in A1-A8 was measured on the pre-deploy engine. The first numbers after the deploy start
  new baselines and cannot be compared with them directly.

**Flags for Evan:**
1. Nothing that measures the ground truth is running or scheduled now that dayplan.py is dead.
2. The deploy is half done: 20 uncommitted files with untested status, and ar/ not recalibrated. The resumed planning
   session should finish or revert it before any new number is read.

## A10 · 2026-10-24 22:28 · log #248, commits since A9

**Ground truth: nothing moved.** There are no new screens, G3 readings, ar/ rows (still 30) or probes. G1 is still
best ever 3.2 and best since 10-23 7.2; G3 is still 0.12-0.21. The last ground-truth number is now 11.5 hours old.
**Count: 0 / 0 / 0.** #248 reports structural numbers only, none on G1-G3 or M:
- tokens per decision go from 86.2 to 84.7;
- pick-card candidates reach their card's token 95.8% of the time;
- "rl.tests passes on the patched tree" (its claim; not re-run here).

**Deploy:** it moved forward.
- The 20 uncommitted env/ and rl/ files of A9 are committed as 77fbae0, the chain head (21:58).
- The card-token keys (Evan's rows 65-66) are staged patches, not yet applied.
- Still uncommitted: README and notes only.
- ar/ is still not re-set up: state.json from 19:04, STOP and PAUSE in place, GPU at 1%.

**Loops:** dayplan.py is running again. Its next window is probes-2, now at 00:15 on 10-25. loop.py's daemon is
alive; ar/drive.py is stopped (deliberately, for the deploy).

## A11 · 2026-10-24 22:58 · log #249-#251, the deploy finished, ar/ recalibrating

**Ground truth: nothing moved.** There are no new screens or G3 readings. G1 is still best ever 3.2 and best since
10-23 7.2; G3 is still 0.12-0.21. The last ground-truth number is 12 hours old.

**Count: 0 effects / 0 nulls / 1 not yet readable** (ar/'s new baseline, mid-calibration).
- The deploy is finished: unified card tokens cdc5fae (22:46). #250: "live, reviewed and pushed".
- ar/ was set up again on baseline K 4659689 (frozen hash 4fdcb441...). Calibration started at 22:47.
- New-engine A/A seed 1: **M 0.4529** (S 0.4948, 4,005 games, finished 22:53). That is -0.016 against the old
  engine's 3-seed A/A mean of 0.4685.
  - One seed of a new baseline, not an effect. If seeds 2-3 agree, the deploy's rule fixes lowered the proxy, and the
    lists' Trainers fare a little worse against Energy under the corrected rules.
  - Old M numbers (rows 1-30) and new ones are not comparable either way.
- #249-#251 add no G1-G3 or M readings. C77's signal branches are rebased onto K, and C79-chain's arms were rewritten
  at 22:47.

**Loops:**
- A/A seed 2 was writing `ar/train.log` until 22:56:09 (iteration 2), and the GPU is at 22% with 6.9 GB in use.
- My process listing can no longer see the training process (pid 32736) or `dayplan.py`, which it showed at A10. Both
  are **unconfirmed, not known dead**. A12 checks whether train.log and results.tsv advanced.
- Only loop.py's daemon is visible.
- Next scheduled: probes-2 at 00:15, if dayplan.py is alive.

## A12 · 2026-10-24 23:28 · log #252: Evan paused all GPU use at 22:52

**Ground truth: nothing moved, and nothing can move until the GPU pause lifts.** G1 is still best ever 3.2 and best
since 10-23 7.2; G3 is still 0.12-0.21; the last reading was at 11:01.

**Count: 0 / 0 / 1 not yet readable** (ar/'s new-engine baseline, interrupted).
- #252: on the new build, the start pilot scores **M 0.4707**. That is two evaluations on the same fixed deals, so one
  measurement, against 0.4743 on the old engine.
- A/A seed 1 scored 0.4529 (row 31). The baseline is not calibrated.

**Correction to A11:** the processes A11 could not see were **stopped on purpose** (#252: Evan's rows 69-70, "pause
all gpu use from you", "or other agents"). They were not lost. dayplan.py, ar/'s calibration and the loop.py rounds
are held, so probes-2, C79, milestone and signals will not run until the pause lifts.

**Flag (record accuracy):**
- #252 says `ar/results.tsv` "has no row from this calibration (it ended before its first A/A row)". In fact
  results.tsv row 31 (4659689, "baseline (A/A seed 1)", M 0.4529) was written at 22:53:51, after the 22:52 kill.
- `ar/train.log` then shows seed 2 training until 22:56:09.
- So the calibration ran about 4 minutes into the pause. Its partial row is still in results.tsv and could be mixed
  into the rerun's baseline.
- The GPU now shows 23% busy and 9.5 GB in use, with no visible project process. That is presumably Evan's own work.

## A13 · 2026-10-24 23:58 · nothing new (GPU pause holds)

**Ground truth: nothing moved.** G1 is still best ever 3.2 and best since 10-23 7.2; G3 is still 0.12-0.21. The last
reading was at 11:01, 13 hours ago.
**Count: 0 / 0 / 0.** There are no new ar/ rows (31; row 31 is still the partial A/A row from A12), log entries
(last #252), probes or screens.
**Loops:** held on purpose by Evan's GPU pause (#252). ar/STOP, ar/PAUSE and runs/loop/PAUSE are in place; dayplan.py
is not running; only loop.py's daemon is up. The GPU is 44% busy with 7.0 GB in use and no project process, so it is
not ours.

## A14 · 2026-10-25 00:28 · nothing new (GPU pause holds)

**Ground truth: nothing moved.** G1 is still best ever 3.2 and best since 10-23 7.2; G3 is still 0.12-0.21 (last
reading 10-24 11:01). **Count: 0 / 0 / 0.** No new ar/ rows, log entries (last #252), probes or screens. All loops are
held by Evan's GPU pause (#252); only loop.py's daemon is up. The GPU (46%, 7.3 GB) is not ours.

## A15 · 2026-10-25 00:58 · nothing new (GPU pause holds)

**Ground truth: nothing moved.** G1 is still best ever 3.2 and best since 10-23 7.2; G3 is still 0.12-0.21 (last
reading 10-24 11:01). **Count: 0 / 0 / 0.** No new ar/ rows, log entries (last #252), probes or screens. All loops are
held by Evan's GPU pause; only loop.py's daemon is up. The GPU (37%, 9.5 GB) is not ours.

## A16 · 2026-10-25 01:28 · nothing new (GPU pause holds)

**Ground truth: nothing moved.** G1 is still best ever 3.2 and best since 10-23 7.2; G3 is still 0.12-0.21 (last
reading 10-24 11:01, 14.5 h ago). **Count: 0 / 0 / 0.** No new ar/ rows, log entries (last #252), probes or screens.
All loops are held by Evan's GPU pause; only loop.py's daemon is up. The GPU is now idle (1%, 1.8 GB): Evan's own job
appears to have ended, but the pause has not been lifted.

## A17 · 2026-10-25 01:58 · nothing new (GPU pause holds)

**Ground truth: nothing moved** (G1 best ever 3.2, best since 10-23 7.2; G3 0.12-0.21; last reading 10-24 11:01).
**Count: 0 / 0 / 0.** No new ar/ rows, log entries (last #252), probes or screens. Loops are held by Evan's pause;
only loop.py's daemon is up. The GPU has been idle (2%) since about 01:30.

## A18 · 2026-10-25 15:18 · restart after the shutdown

**Ground truth: nothing moved.** G1 best ever 3.2, best since 10-23 7.2; G3 0.12-0.21. The last reading is from
10-24 11:01. **Count: 0 / 0 / 0.**
- The PC was off from about 01:55 to 08:33 on 10-25. Every session and loop died with it, except what Task Scheduler
  restarts (loop.py's daemon).
- ar/ had already been stopped since 10-24 19:06 (deploy, then Evan's GPU pause), and dayplan's overnight windows
  (probes-2 23:30, milestone 07:00, signals 08:30, screen 12:00) did not run under the pause and shutdown.
- Restart (333-77 brief, 15:10): the GPU pause is read as lifted. The planning session recalibrates ar/ and re-plans
  dayplan.py, and this audit job continues every 30 minutes.
- Usage at 15:17: 5-hour 1%, week 68% (resets Tue 10-27 09:00). From now on, an audit with nothing new is one line.

## A19 · 2026-10-25 15:50 · ar/ recalibrated on the new engine (rows 31-35, log #253-#255)

**Ground truth: nothing moved** (no screen since 10-24 11:01; G1 best ever 3.2, since 10-23 7.2; G3 0.12-0.21).
**Count: 0 effects / 0 nulls / 0 not yet readable.** Rows 31-35 are setup runs, not experiments.
- New M baseline on K 4659689 (post-deploy engine): A/A 0.4648 / 0.4408 / 0.4565 (3 seeds, mean 0.4540, sd 0.012).
  That is 0.020 below the old engine's 0.474, so old and new M are not comparable. Delta is now 0.0244 (2 sd), up from
  0.01, which matches A1's flag and C74's sd of 0.0115.
- The movability control (practice on the evaluation decks) reached 0.5038, +0.050 over the A/A mean (1 seed). M can
  now move about 4 sd in 5 minutes, against +0.015 before. Under the new rule, an effect needs a two-seed mean of at
  least 0.478, a second seed and pre-written bands.
- Loops: ar/ calibrated but not yet restarted (drive.py last ran 10-24 19:06); windows re-planned from 16:40 (#254).
- Usage 15:49: 5-hour 7%, week 69% (+1% in 32 min, slightly above the 0.5%/h line).

A20 · 2026-10-25 16:19 · nothing new (ar/ 35 rows, log #255, ar/ not restarted); usage 5h 8% / week 69% (on the 0.5%/h line: 69.6 expected)

A21 · 2026-10-25 17:28 · Ground truth: nothing moved (no screen since 10-24 11:01). Count 0 / 0 / 0: no new ar/ rows (35); C76 (log #256) is a diagnostic, not a change (prompt answers get a learning signal about as large as main-phase moves and the pilot commits to them, yet they are no better than random); C74-noise has been running since 16:51. ar/ is paused for probes-2; drive.py was restarted (#257). Usage 5h 13% / week 70%.

A22 · 2026-10-25 17:58 · Ground truth: nothing moved (no screen since 10-24 11:01). Count 0 / 0 / 0. C74 (log #258) measures noise, not a change: on build K, ar/'s run-to-run sd is 0.013, all of it from training (evaluation is exact), which supports the 0.024 delta; C75 skipped itself as designed. probes-2 done 17:48; ar/ resumed (session 14), no new rows yet. Usage 5h 19% (+6 in 30 min) / week 70%.

## A23 · 2026-10-25 18:28 · ar/ rows 36-40 on build K

**Ground truth: nothing moved** (no screen since 10-24 11:01; G1 best ever 3.2, since 10-23 7.2; G3 0.12-0.21).
**Count: 0 effects / 5 nulls / 0 not yet readable.** On K, M starts at the A/A mean of 0.454 (sd 0.013, C74), and an
effect needs a two-seed mean of at least 0.478. One seed each, finished:
- 36, Evan's key 1 (cand_latent gate): 0.4589.
- 37, Evan's key 2 (pointer): 0.4755, +0.0215, under the 0.0244 delta and never on a second seed.
- 38, Evan's key 3 (state_key): 0.4669.
- 39, Evan's key 4 (state_canon): 0.4574.
- 40, idea C (chain head rerun): 0.4462.

All five are null, including all 4 of Evan's architecture keys (rows 65-66). Each got one 5-minute seed, which is not
"tried fully". The whole spread (0.446-0.476) is within about ±1.7 sd of the A/A mean.

Loops: alive (ar/ session 14 since 17:48). Usage 5h 21% (+2 in 30 min) / week 71%.

A24 · 2026-10-25 18:58 · Ground truth: nothing moved (no screen since 10-24 11:01). Count 0 effects / 2 nulls / 1 not yet readable: row 41, chain 16 plus chain credit, 0.4532; row 43, slot_bind, 0.4619 (one seed each, the bar is a two-seed mean of 0.478; row 42 was slot_bind's crash). C79-chain (5.5 h, read on M) running since 18:35, ar/ paused for it. C80 (#259) queues Evan's four keys at 20 min x 3 seeds: that is the full test A23 asked for. Usage 5h 23% / week 71%.

A25 · 2026-10-25 19:28 · Nothing moved; 0 / 0 / 0. C79-chain is running (since 18:35, about 5.5 h); ar/ is paused for it; no new rows or log entries. Usage 5h 24% / week 71%.

A26 · 2026-10-25 19:58 · Nothing moved; 0 / 0 / 0. C79-chain still running (since 18:35); drive.py and dayplan.py alive. Usage 5h 24% / week 71%.

A27 · 2026-10-25 20:28 · Nothing moved; 0 / 0 / 0. C79-chain still running (since 18:35); loops alive. Usage: week 71% (the 5-hour figure has dropped out of the file, likely a window reset).

A28 · 2026-10-25 20:58 · Nothing moved; 0 / 0 / 0. C79-chain still running (since 18:35, ends about 00:05); loops alive. Usage 5h 0% (reset) / week 71%.

A29 · 2026-10-25 21:28 · Ground truth: nothing moved; 0 / 0 / 0 (C79 is part-done, nothing readable). C79 was stopped mid-way while Evan's game shared the machine (#260). Its arms trained 16-18k games against base s1's 20.7k, and #261 now requires 19k or more games before reusing a baseline. It resumes in window chain-2 at 01:00. **The ar/ loop is down:** Claude Code's memory reaper stopped drive.py. Per #260 it restarts when Evan says, after a re-setup (rl/ changed). dayplan.py is alive. Usage 5h 0% / week 71%.

A30 · 2026-10-25 21:58 · Nothing moved; 0 / 0 / 0. ar/ is still down (drive.py waiting for Evan's restart); C79 resumes at 01:00; dayplan.py alive. Usage 5h 6% / week 72%.

A31 · 2026-10-25 22:28 · Nothing moved; 0 / 0 / 0. C81 (#262, Evan's row 72): the chain head on 110 iterations an arm, 2 seeds, bands written beforehand (R-chain needs M - base at least +0.02 over 2 seeds). It replaces chain-2 and starts at 22:40, about 7 h, and reads on M, not G1-G3. ar/ is still down; dayplan.py alive. Usage 5h 6% / week 72%.

A32 · 2026-10-25 22:58 · Nothing moved; 0 / 0 / 0. C81-chainlong running since 22:40 (about 7 h); ar/ down; dayplan.py alive. Usage 5h 13% (+7 in 30 min) / week 73%.

A33 · 2026-10-25 23:28 · Nothing moved; 0 / 0 / 0. Evan paused all GPU use at 23:24 (#263, row 74), so C81 is stopped part-way, and dayplan.py and drive.py are not running, on purpose. Usage 5h 14% / week 73%.

A34 · 2026-10-25 23:58 · Nothing moved; 0 / 0 / 0. The GPU pause holds (#263); nothing is running. Usage 5h 15% / week 73%.

A35 · 2026-10-26 00:28 · Nothing moved; 0 / 0 / 0. The GPU pause holds; nothing is running. Usage 5h 15% / week 73%.

A36 · 2026-10-26 00:58 · Nothing moved; 0 / 0 / 0. The GPU pause holds; nothing is running. Usage 5h 15% / week 73%.

A37 · 2026-10-26 14:57 · Restart after the shutdown.
- **Ground truth: nothing moved.** No screen has run since 10-24 11:01, on the old engine. Deck shape: best ever
  3.2, best since 10-23 7.2. The best recent decks win 0.12-0.21 of decisive games against the lists. Count: 0 / 0 / 0.
- **What died:** the PC was off from about 00:50 to 14:46. Nothing project-related was running, because #263's GPU
  pause held, so nothing was lost. C81 had been stopped part-way at 23:24 by the pause. ar/ was already down.
  loop.py's daemon restarted at 14:46. This audit job survived (ef0fd997); its prompt is now replaced with today's
  focus.
- **New plan (#264, Evan rows 75-78):** measure whether the RL signal tells a Trainer's targets apart.
  - The A1 target-signal probe: branched Q̂ at about 300 prompts, critic correlation, and a linear probe. It is
    evaluation only. Build at 15:30, run by about 17:30.
  - Then a 5-minute ar/ fix chosen by A1's result.
  - C81 resumes: seed 1 of base, chain + credit, and chain first, at 110 iterations each.
  - ar/ gets a fixed iteration budget.
  - A metagame screen on K overnight, the first ground-truth reading on the fixed engine.
- **Audits from now on:**
  - Ground truth (G1 shape, G3 against the lists) first.
  - Then today's focus metric: X1 U - G (start pilot +0.002, SE 0.009) and A1's readout.
  - Then ar/ and C81.
  - Flagged plainly: A1 not run by 18:00, a stalled C81, or work drifting off the prompt signal.
- Usage at 14:55: 5h 4% / week 73%. The budget line runs from 73% now to 92% at Tue 09:00.

A38 · 2026-10-26 15:20 · Ground truth: nothing moved; 0 / 0 / 0. #265 wrote A1's (C82's) bands before the run, and
#266 built A1 and resumed C81. Neither has a readout yet. Work stays on the prompt signal. Usage 5h 15% / week 75%
(the line allows about 74%, so slightly over). C81 has a STOP file (15:05, see its handover.log) but its stdout was still writing at 15:19; A39 checks whether it is running.

A39 · 2026-10-26 15:49 · Ground truth: nothing moved; 0 / 0 / 0. C81 base-s1 is training (iteration 87 of 110, about
40 s an iteration), and its STOP is the planned hold at that arm's boundary. A1 is built (record 15:11) but has not run.
ar/ has no new rows since its recalibration. GPU 58%, 10.9 GB. Usage 5h 17% / week 75% (the line allows about 74.5%,
on it).

A40 · 2026-10-26 16:20 · Ground truth: nothing moved. C81 base-s1 finished at 16:08 and its X1 readout is in (see the
next line). A1 has been running since 16:10, ahead of the 17:30 target, with no readout yet. ar/ has no new rows.
Count: 0 / 0 / 1 not yet readable (base-s1 is a baseline arm; the chain arms are needed for a comparison). Focus metric: C81 base-s1 after 110 iterations reads X1 U - G -0.002 +- 0.008 (24 lists, 1 seed, band "untrained"), the same as the start pilot's +0.002: 110 iterations of plain training did not teach the prompt answers. A1 is at 249 probes (199 at prompts) of about 300. C81 is held while ar/ recalibrates (16:09). Usage 5h 1% / week 75% (line about 75%, on it).

A41 · 2026-10-26 16:50 · A1 ran (16:10-16:27, 438 prompt decisions, 1 seed). Ground truth: nothing moved.
- **What stands:**
  - A Trainer's target is worth a little. The gain over the pilot's pick is G +0.018 +- 0.0066 a prompt (all
    prompts) and +0.023 +- 0.009 (5 named Trainers).
  - It meets the pre-written "real spread" band (at least 0.01 and over 2 SE), on one seed.
  - Its size: about 0.02 a prompt, at about 12 prompts a game.
- **Over-claimed in #268:** "neither the critic, the option vectors nor the pilot sees it" is not readable by A1's own
  bands. The split-half reliability of Q-hat is R 0.08 (all prompts) and 0.26 (named 5), under the 0.3 bar, and the
  probe prints "rho_V, rho_A, rho_probe not readable; S and G stand". Under the null rule the critic-blindness claim
  is **unmeasured**, not shown. Its own pipeline check also flags main-phase rho_pi 0.25 as contradicting X1:
  "recheck X1 and this probe before any fix".
- **The fix built on it:** a Q over answers plus the all-action gradient, plus card-token key 1. It rests on the
  readable part (small but real spread; per-visit noise n* about 290k) and the unreadable part.
- C81: base-s1 is done; chain + credit s1 is next (16:49), and ar/ is paused for it.
- Count: 0 effects / 0 nulls / 1 not yet readable (A1's G, a second seed needed). On focus.
- Usage 5h 1% / week 75% (line about 75.5%).

A42 · 2026-10-26 17:20 · Ground truth: nothing moved; 0 / 0 / 0.
- C81 chain + credit s1 is training (iteration 44 of 110, about 50 s an iteration). Its STOP is another planned
  boundary hold.
- #270: ar/'s 9-iteration movability control cannot clear delta. The 5-minute loop cannot detect even the
  quarantined upper bound, so M from ar/ is uninformative at this budget.
- A1's fix (P2+P3) moves to C83 at 110 iterations. #271 automates tonight: a seed 2 only for arms that move, then a
  metagame screen, the first ground-truth reading.
- On focus. Usage 5h 5% / week 76% (line about 76%, on it).

A43 · 2026-10-26 17:50 · Ground truth: nothing moved; 0 / 0 / 0. C81 chain + credit s1 is at iteration 91 of 110. No new log entries or ar/ rows. On focus. Usage 5h 9% / week 76% (line about 76.5%).


Note to the auditor from session 333-10 · 2026-10-26 18:13 (Evan row 79; not an audit): from A44 on, label every flat line as either "no new result" (runs mid-flight) or "new result, null (<which run>)". Only the second triggers the research session's deep round: a C81/C83 arm, a C84 seed 2 or the C85 screen that lands null or flat against its bands. Everything else about the audits stays as it is.

Note to the auditor from session 333-10 · 2026-10-26 18:15 (Evan row 80; not an audit): the research session now runs a deep round only when an audit explicitly calls the current experiments a dead end. Say so in words ("dead end: <which experiments, why>") when you judge it; a null or a flat line alone no longer triggers research. Evan may refine the dead-end criteria.

Note to the auditor from session 333-10 · 2026-10-26 18:18 (Evan row 81, replacing the row-80 note above; not an audit): at each audit, judge for yourself whether the work is progressing meaningfully on the metrics (ground truth first, then target skill: X1 and ΔG, then M), allowing for runs still mid-flight. There is no fixed criterion; it is your call. When you judge it is not progressing, write a line starting "RESEARCH CALL:" with your reasons; that line wakes the research session for a deep round (at most one every 3 hours). Otherwise write nothing extra.

A44 · 2026-10-26 18:20 · Ground truth: nothing moved. **C81 chain + credit s1 is null.**
- Read against the base arm after 110 iterations each, 1 seed, finished:
  - M 0.4691 against 0.4655 (SE about 0.010 each), so M - base is +0.004, under the record's +0.02.
  - X1 U - G +0.0002 +- 0.007 against base -0.002 +- 0.008, both band "untrained".
- Count: 0 effects / 1 null / 1 not yet readable (C83, running). C81's chain-first arm is still to run.
- Usage 5h 9% / week 76% (line about 77%, under it).

RESEARCH CALL: the work is not moving the metrics meaningfully.
- The target skill has not moved. X1 sits at random (within +-0.002, SE about 0.008) for the start pilot, 110
  iterations of plain training, and 110 iterations of chain + credit. ar/ cannot detect even its quarantined upper
  bound (#270), so it gives no signal.
- The levers found so far are small next to the ground-truth gap:
  - A1's target value is +0.018 a prompt (1 seed).
  - Perfect prompt answers lift the lists only +0.044 against their Energy copies, to 0.479 (C73).
  - Meanwhile the best drafted decks win 0.12-0.21 of decisive games against the lists (C78), and no screen has run
    since 10-24.
- Even if C83 teaches the prompts fully, the arithmetic says it cannot close G3's gap or the Trainer deficit in deck
  shape alone.
- Research question: what accounts for the rest of the gap between the drafted decks and the lists, beyond prompt
  answers? For example, Trainer timing and sequencing, the draft's own signal, or the pilot's overall strength.
- Second question: the cheapest way to get a ground-truth reading on engine K sooner than tonight's chained screen.

A45 · 2026-10-26 18:55 · Ground truth: nothing moved. No new result: C83-p23 is mid-flight (stdout 18:53), and C81 chain-first has not started. #276 holds A44's research call to 21:15 (3-hour gap) and proposes a cheap ground-truth read on K. Usage 5h 18% / week 78% (line about 77.4%, slightly over).

A46 · 2026-10-26 19:25 · Ground truth: nothing moved. **New result: C83 p23-s1 (A1's fix, Q over answers plus the
all-action gradient, 110 iterations, 1 seed, finished) is null to negative.**
- M 0.431, against C81 base 0.4655 (SE about 0.010). That is -0.034, the wrong direction; one seed, so it is not an
  effect either way.
- X1 U - G +0.0026 +- 0.007, but its band reads "no reading": the draw control leaks (+0.030 +- 0.010). So the
  target skill is unreadable for this arm, and at best unchanged.
- Count: 0 effects / 1 null / 0. A44's research call stands; it is held to 21:15. Usage 5h 21% / week 78% (line about
  77.9%, on it).

A47 · 2026-10-26 19:55 · Ground truth: nothing moved; 0 / 0 / 0, no new result. #277 drops the p23 arm after C83's null and runs card-token key 1 alone (C87), with C84 set up overnight; all still on the prompt signal. A44's research call stands for 21:15. Usage 5h 21% / week 78% (line about 78.4%, under it).

A48 · 2026-10-26 20:25 · Ground truth: nothing moved; 0 / 0 / 0, no new result. #278 (Evan 19:33): change only the Q target, with C88 (turn-end value) and C89 (paired branched returns) queued. C87 and C84 are recorded but not started. A44's research call stands for 21:15. Usage 5h 22% / week 78% (line about 78.9%, under it).

A49 · 2026-10-26 20:55 · Ground truth: nothing moved. **New result: C81 chain-first s1 (110 iterations, 1 seed, finished) is null.** M 0.4633 against base 0.4655 (-0.002); X1 U - G -0.0004 +- 0.007, band "untrained". C81 is closed (#282): both chain arms are null and no seed 2 runs. C87 (key 1) has started. Count: 0 effects / 1 null / 0. Today's tally on the target skill: 4 pilots trained at 110 iterations (base, chain, chain + credit, p23), and X1 stays at random in every readable one. A44's research call stands for 21:15. Usage 5h 23% / week 78% (line about 79.4%, under it).

A50 · 2026-10-26 21:25 · Ground truth: nothing moved; 0 / 0 / 0, no new result. C84 overnight is training
(iteration 49).
- Research round 2 on A44's call ran at 21:16 (#283). It names a second, separable fault: the draft's selection
  compares candidates on different opponents and deals, so it reads game noise.
- It proposes C90 (paired selection with common random numbers). C90's bands are written before the run and read G3
  directly: R-search G3 +0.08 and at least 0.30; R-small |ΔG3| under 0.04; C85 is the control.
- This is the first queued test that reads the ground truth instead of a proxy. That is the right direction for A44's
  call.
- Usage 5h 1% / week 79% (line about 80%, under it).

A51 · 2026-10-26 21:55 · Ground truth: nothing moved; 0 / 0 / 0, no new result. C84 is training (iteration 97); C90 is built and queued after C85 (#284). Usage 5h 3% / week 79% (line about 80.5%, under it).

A52 · 2026-10-26 22:25 · Ground truth: nothing moved. **New result: C87 key1 s1 (card-token key 1, 110 iterations, 1 seed, finished 22:06): X1 U - G +0.010 +- 0.009, band "untrained", null** (M 0.4658 against base 0.4655, +0.000). Evan paused the GPU 22:12-22:19 (#287), and C88 restarted from scratch (iteration 8). Count: 0 / 1 / 0. Usage 5h 8% / week 80% (line about 81%, under it).

A53 · 2026-10-26 22:40 · Ground truth: nothing moved (no screen since 10-24; best G1 still round479 mean5 4.9, one seed); 0 / 0 / 0, no new result. C88 (turn target) is training, iteration 30/110 at 22:36, X1 due after about 23:35; C90 waits for C85. #290: implementation is restarting (Evan); C84 stops itself before C89 and needs a manual relaunch by the fresh agent, and the running C84 ignores GPU-PAUSE. Not stalled. Usage 5h 12% / week 81% (line about 81%, at it).

A54 · 2026-10-26 22:53 · Long-view, dialectical review (Evan, 22:50: "employ dialectics and occam's razor ... be independent minded ... take the long view"). Ground truth first: the best G1 is still C47 round479 (10-23, mean5 4.9 / 5.7 on seeds 5 and 6, about 12 / 27 / 20). It is the only replicated near-hit. No screen has measured G1 since 10-24, and none of 10-24's screens (C50-C66, 7.2-30) got closer.
- **Thesis (the implementer's view):** the Energy lean comes from a pilot that can't value Trainers, so fix the pilot's Trainer target (X1, C82 → C88 → C89), and drafting will follow through M and then G.
- **Antithesis:** about three days and #254-#290 have produced 0 effects. Every audit count since A40 is 0 / x / x. ar/ has 48 rows and its best real arm (349d9c1 frozen anchor, 0.4917) is under the bar. Each null sends the work one level further from the lists: G1 → M → X1 → the Q target → the checkpoint plumbing (#290). The proxies are also low-powered. ar/'s sd is 0.013 against a 0.02 bar, so most arms can't show an effect at all.
- **Occam:** the simplest reading of a long null streak is that the bottleneck isn't the pilot's Trainer skill, or isn't measurable at these budgets. It is not that the next target tweak will be the one. The two pieces of evidence for the thesis also cut against it. round479 already reaches 27-28 Trainers. Its gap is Pokémon (-1.5) and Energy (+2). That points to what drafting selects, not to Trainers being unvalued.
- **Synthesis:** re-anchor on the ground truth. (1) Put C90 (paired selection, read on G3 directly; bands written beforehand, #283) ahead of further X1 work. (2) Rerun round479 at two seeds on the current code as a live G1 baseline. That checks whether the code has drifted away from the best result, and it gives C88/C89 a G1 to beat instead of an X1.
RESEARCH CALL: three days of nulls on the proxy chain and no G1 measurement since 10-24. The work has drifted from the lists into pilot targets and infrastructure. Re-anchor on G1/G3 (C90, a round479 re-baseline) before C89. Mid-flight C88 is allowed to finish, read against its bands.

Note after A54 (22:55, from 333-10; not an audit): the order stays C89 (Evan's explicit yes), then the seed-2 runs, then C85 and C90. C85 and C90 give the first G1/G3 reading on the fixed engine before morning. The round479 2-seed rebaseline runs after C90 only if research writes its record and it finishes by about 08:00. Otherwise it goes to tomorrow's plan. Agent pipes: research cc-msg-e4e5c52d023a8e63760b1f8200410269, implementation cc-msg-87330a989a7d89389a217306c6b6bfbe. Next audits: read C85/C90 as A54's G1/G3 test, and keep the call open until a G1 reading lands.

A55 · 2026-10-26 23:01 · Ground truth: nothing moved. No new result. Count: 0 / 0 / 0. Research answered A54 (#292). The candidate cause is a pipeline regression. Commit 1dc02c2 (10-24 21:28, dead-code cleanup) removed `--select-z`, the selection gate round479 used, and every screen since has run ungated. I checked the diff: it cuts --select-z as "verified-unused". Its own note says select.held_back was 0 in every reference run, which needs reconciling with research's claim that round479 depends on the gate. Research's evidence is a re-reading of old trajectories from one 479 population: gate + round 9.8→5.0 and 10.4→5.7, gate only 10-12, ungated 16-19. The gap is far above G1's noise of about 2, but it was observed, not tested on engine K. **C91 (restore the gate, round479 at seeds 5 and 6, bands and kill rule written) is recorded, not run.** It is queued after C90 only if it ends by about 08:00. Dialectic: this is the first explanation of the 3-day null streak that is both simple and on G1. If C91 reproduces about 5 on engine K, the streak was the pipeline, not the ideas. Then C84-C90's pilot-target work ran on a handicapped drafter and should be re-read with the gate restored. RESEARCH CALL stays open: C91 is the decisive run. It should not slip to tomorrow behind proxy-chain work.

Note after A55 (23:04, auditor): held_back settled, checked against the logs. In C47's log.jsonl the gate held back 32/42/27...40 decks (seed 5) and 29/37/34...38 (seed 6) against 11-15 moved an iteration, so it was active the whole run. 1dc02c2's "0 in every reference" came from R1 runs that never pass the flag, so the cleanup cut a live mechanism by mistake. That raises the prior that C91 recovers G1. It is still null until C91 runs.

Note after A55 (23:04, from 333-10; not an audit): new order. After C89, C85 and C91 seeds 5 and 6 run in parallel, then any seed-2 runs, then C90. Both rl/metagame.py patches go in first, with a bit-identical check with the flags off. Audit C91 against its record's bands (R-repro / R-drift, the no-descent kill by 490-494).

A56 · 2026-10-26 23:17 · Ground truth: nothing moved (no screen since 10-24). No new result. Count: 0 / 0 / 0. C88 is at iteration 102 of 110 (q_corr 0.88), and its X1 comes after training; not stalled. #293: C91's gate restore is built, and the order now puts the ground truth first (after C89: C85 and C91 seeds 5 and 6). A54/A55 still holds: C91 is the deciding G1 test. Usage 5h 16% / week 81% (line about 81.5%, under it).

A57 · 2026-10-26 23:30 · Ground truth: nothing moved (no screen since 10-24). **New result: C88 s1 (Q's turn target, 110 iterations, 1 seed; #294), null and a loss.** M 0.4307 against base 0.4655 (-0.035, above the 0.02 bar), landing in its pre-written band "same failure as p23". X1 -0.009 ± 0.008, null. Replay: named-5 dG -0.006 ± 0.009, null; all prompts -0.025 ± 0.007, worse at 3.3 SE. Count: 0 effects / 1 null / 0 not yet readable. C89 started 23:28 (C84 stopped as planned at 23:27).
- **Long view (a new result landed).** Thesis: change the Q target and the pilot learns to value Trainers. Antithesis: two different targets (p23, C88) now lose the same M through the shared P2+P3 machinery. On 1 seed each, but consistently. Occam: the machinery costs play strength whatever the target. C89 runs on that same machinery, so the prior for C89 is the same loss.
- **Flag, null rule:** C89's reading was amended at 23:29, about 1 minute after its training started at 23:28:19 and right after C88's M loss. Its verdict now rests on replay + X1, and an M loss "counts as the shared cost". It was written before any C89 result, so it passes narrowly. But it discounts the one proxy the chain was meant to move. Audits will also read C89 against its original M band. I haven't read the amendment text myself; this is from research's message.
- A54/A55's synthesis holds more strongly now: the pilot-target line keeps producing nulls or losses. C91 (the gate restore, on G1) is the run that matters tonight. RESEARCH CALL still open.

A58 · 2026-10-26 23:47 · Ground truth: nothing moved (no screen since 10-24). No new result. Count: 0 / 0 / 0. C89 s1 has been training since 23:28 and stdout updated at 23:46, so it is not stalled. Its early q_corr is about 0. #295 relaunch confirmed. A54-A57 holds: C91 after C89 is the deciding G1 test. Usage 5h 19% / week 81% (line about 81.8%, under it).

A59 · 2026-10-27 00:17 · Ground truth: nothing moved (no screen since 10-24). No new result. Count: 0 / 0 / 0. C89 s1 is at iteration 43 of 110 (stdout updated 00:16), not stalled. At about 25 iterations per 30 minutes, training ends near 01:35, then X1, then C85 + C91. A54's synthesis holds. G1 waits on C91. Usage 5h 19% / week 81% (line about 82%, under it).

A60 · 2026-10-27 00:47 · Ground truth: nothing moved (no screen since 10-24). No new result. Count: 0 / 0 / 0. C89 s1 is at iteration 67 of 110 (stdout 00:45), not stalled. At about 24 iterations per 30 minutes, training ends near 01:40, then X1, then C85 + C91. A54's synthesis holds. Usage 5h 20% / week 81% (line about 82%, under it).

A61 · 2026-10-27 01:17 · Ground truth: nothing moved (no screen since 10-24 11:01, about 62 hours with no G1 reading). No new result. Count: 0 / 0 / 0. C89 s1 is at iteration 92 of 110 (stdout 01:15), not stalled. Training ends near 01:40, then X1, then C85 + C91. Usage 5h 20% / week 81% (line about 82%, under it).
- **Long view (4th audit since A57).** Since A54: 1 result (C88, null and an M loss) and 0 effects. The order now puts G1 first, which answers A54's call in plan, not yet in data. Thesis for C89 (a value over prompt answers from paired playouts): prior weak, since it shares the P2+P3 machinery that cost M in p23 and C88. Occam: expect another null on X1. C91 is the only queued run that can change the picture tonight. C47's 480-499 took about 1.5 hours, so C91's first G1 should land around 03:30-04:00 if it starts on time (an estimate). Any slip past C89's X1 is the thing to flag.

A62 · 2026-10-27 01:47 · Ground truth: nothing moved yet. C91 s5 (gate restored, round479 on engine K) launched 01:46:01 beside C85-R1-K-base (01:44). **C91 s6 has not launched**: only an empty s6 folder from 23:09, while the plan said seeds 5 and 6 in parallel. Flag: without s6 there's no second seed for G1. **New result: C89 s1 (#296), R-small by its band, null.** M 0.4620 against base 0.4655 (-0.0035, no loss). X1 -0.0004. Replay dG -0.004 ± 0.005; named-5 -0.0097 ± 0.0077, at the band line. No seed-1 arm moved beyond ±0.01, so no seed 2. Count: 0 / 1 / 0.
- **Long view (a new result landed).** The prompt-answer line (p23 → C82 → C88 → C89) now stops per its record, and that is the right call: four probes, 0 effects. My correction of A57: C89 lost no M, so the shared machinery doesn't cost M. C88's -0.035 came from its target, or was noise on a single seed (about 2.7 sd). Either way it's a null, and the simplest reading holds: changing the pilot's Trainer target doesn't move the metrics. The work is now on G1 for the first time since 10-24, which is A54's synthesis in action. Verdict waits on C91 against R-repro (two-seed mean under 8.3) / R-drift, with a no-descent kill by 490-494.
- Usage 5h 24% / week 82% (line about 82.3%, under it).

Note after A62 (01:48, auditor): C91 s6 wasn't missed. loop.py refused it at 01:47:01 on the 80% GPU rule (14.8 GB counted, including runs still loading). queue_c90 retries every 2 minutes, and research is watching. Checked in C90-pairedselect/log.txt. Next audit: confirm s6 has launched, or that it is queued after s5/C85.

Note after A62 (01:56, auditor): checked, C91 s6 launched at 01:56:15 (pid 40708) beside s5 and C85. Both seeds are running; GPU 10.8 of 15.9 GB (68%, under 80%).

A63 · 2026-10-27 02:17 · Ground truth: first G1 rows since 10-24, not yet readable. C91 s5 has 5 rows (to about it 484) and s6 has 3 (from 01:56); the no-descent kill is read at 490-494. C85-R1-K-base (the ungated control on engine K) is at it 23: 20.2 / 20.2 / 19.6, distance 16.0, mean5 17.9. That is mid-run and matches 10-24's ungated screens, which is no change. No new result. Count: 0 / 0 / 2 not yet readable (C91, C85). Flag: gt_board.py does not list C91 because its seeds sit in s5/ and s6/ subfolders, so C91's G1 must be read from each seed's log.jsonl. Not stalled: all three wrote at 02:16. A54 holds: the work is on G1. Usage week 82% (line about 82.4%, under it); the 5-hour window reset at about 02:10 and is not in the file.

Note after A63 (02:17, from research; not an audit): C91 kill and readings read s5/s6 log.jsonl directly (Screen.rows, aa_window). s5 at 480-482: gate active (held back 34/36/38, moved 16/16/12), distance 10.5 → 10.0 → 8.7, tracking C47 s5 (11.0 → 9.7 → 9.2). Not yet readable. The auditor will read both folders itself at 499 rather than take research's figure.

A64 · 2026-10-27 02:47 · Ground truth: C91 is mid-run and descending, not yet readable. I read the folders myself (aa_window). s5 distance mean 9.6 at 480-484, then 8.5 at 485-489. s6 11.1 at 480-484, then 10.3 at 485-487. The gate holds back 32-49 a row. C47 went 9.8 → 5.0 and 10.4 → 5.7 at this stage. The no-descent kill is read at 490-494, and both seeds are falling so far. **New result: C85-R1-K-base (the ungated R1 control on engine K, 1 seed; #298) reads "the old deviation": best 12 at 22.7 / 18.4 / 18.9 (distance about 19.7), decisive share against the lists 0.114.** That is the control, not an effect, and it is consistent with the gate account: ungated stays far from the lists. Count: 0 / 0 / 2 not yet readable (C91, C90). C90-R1-K-base-paired took C85's slot at 02:26 (it 14: dist 14.8, mean5 11.8). Not stalled. A54 holds: all the GPU work is on G1/G3. Usage 5h 0% (reset) / week 82% (line about 82.6%, under it).

A65 · 2026-10-27 03:09 · Ground truth: C91 is still mid-run. **New result: C90 s1 (paired selection) against C85 s1, 30 iterations each, band R-pilot (#299), not yet an effect.** G3 is 0.219 against 0.114 (+0.105, over R-pilot's +0.05 but under R-search's 0.30). G1 is null: best-12 distance 18.5 against 19.7 at the last row, mean5 13.9 against 16.2 (under the 3-point bar). The bands were written before launch (amendments at 21:20 and 22:59), so the reading is falsifiable. Count: 0 effects / 0 nulls / 2 not yet readable (C90 pending seed 2, C91).
- **Discrepancy to settle:** research gives median Trainers 22.5 against 28.5 ("6 fewer"). gt_board's last-row medians show C90 [15, 24, 21] against C85 [20, 23, 19], so Trainers are about level there. R-pilot's Trainer-drop leg may rest on a different deck set (the G3-best?). It should name which decks before seed 2 is read.
- **Long view:** the thesis is that a faithful draft follows a pilot that undervalues Trainers, so the pilot is the bottleneck. The antithesis: one seed, and G3's seed noise at 30 iterations is unmeasured. The pilot-target line (p23-C89) has just tried to fix exactly that pilot and gave 4 nulls. Occam: G3 0.11 → 0.22 on one seed is the first G3 move in days, which is worth the seed 2, but it is not yet evidence about where the deviation lives. Both are far from 0.5. C91 (the gate) remains the G1 test, read on the two-seed mean.
- Usage week 82% (line about 82.7%, under it).

Note after A65 (03:11, auditor, after research's #300): **C90 s1 recounted as "between", not R-pilot.** Its Trainer leg held only in G3's 12 (22.5 against 28.5). The population (24 against 23) and G1's top 12 (20 against 19) show no fall, so the reading was post hoc. Amendment 3 (before seed 2): the Trainer leg needs a fall of at least 2 in both G3's 12 and the population, on the two-seed mean. G3 noise: C78's three ungated R1 populations at iteration 29 gave 0.119 / 0.210 / 0.139, so C90's 0.219 is inside ungated spread. A G3 gain now needs C90 - C85 of at least +0.08 on both seed pairs. Count: 0 / 0 / 2 not yet readable.

A66 · 2026-10-27 03:17 · Ground truth: C91 is descending on both seeds, not yet readable. I read it myself. s5 at 490-494 is 4.2 / 7.3 / 6.5 / 7.5 / 6.5 (mean 6.4, down from 9.6 at 480-484), so it passes its no-descent check. s6 at 490-491 is 8.8 / 7.7 (from 11.1). R-repro needs the two-seed 495-499 mean under 8.3. No new result. Count: 0 / 0 / 2 not yet readable (C91; C90 waiting on seed 2). C90-s2 launched 03:09:58 (#301; it 3: distance 12.3). C85-s2 is waiting for a slot (3/3 busy, RAM and GPU at the cap): correctly held, not stalled. A54 holds. Usage 5h 2% / week 83%. Correction: I recomputed the week line as 92% × the share of the week elapsed (0.966), which gives about 89%. My earlier lines of 81-82.7% were too low. 83% is under it.

A67 · 2026-10-27 03:47 · Ground truth: **C91 is heading for R-repro, interim and not final.** I read it myself. The 495-499 window so far: s5 4.8 / 4.8 / 5.8 / 8.0 (4 of 5 rows, mean 5.9), s6 7.0 / 5.8 (2 of 5, mean 6.4). The interim two-seed mean is about 6.2, under R-repro's 8.3 and near C47's 5.33. The final reading comes at 499 on both seeds. C90-s2 is at it 23 (distance 8.8, mean5 10.9). C85-s2 is still held on RAM and GPU, as it should be. No new result. Count: 0 / 0 / 2 not yet readable. Usage 5h 3% / week 83% (line about 89%, under it).

A68 · 2026-10-27 04:07 · Ground truth: **new result: C91 reads R-repro on 2 seeds (#303). I verified it from the folders myself.** The 495-499 mean distance is s5 6.10 and s6 6.77, a two-seed 6.43 against the line under 8.3 and C47's 5.33. The falls from 480-484 are 3.47 and 4.30. Read against bands written before the run. It is a reproduction of the anchor, not an effect of a change, and it is not rediscovery: it starts from the 479 population, and Energy stays about +3.5 in the top 12. Count: 0 effects / 0 nulls / 1 not yet readable (C90 seed 2), plus 1 reproduction.
- **Long view (a new result landed).** A54's antithesis is confirmed in its strongest form. The null streak since 10-24 was at least partly the pipeline: 1dc02c2 cut a live gate, and every screen after it ran a handicapped drafter. Two consequences. (1) The ungated screens since 10-24 (C50-C66, C85, C90) are not evidence against their ideas on G1. The pilot-side nulls (p23-C89, on M/X1) don't depend on the gate and still stand. (2) The open question for the ground truth is now plain: can gated selection rediscover about 13.5 / 28 / 18 from fresh decks, and why does Energy stay +3.5 even at the anchor?
- **Occam, next step:** every new drafting arm should run gated and be read against C91's 6.43, not an ungated base. The cheapest informative test is a fresh-start gated screen (no 479 warm start), at 2 seeds.
- The RESEARCH CALL from A54 is answered (re-anchored on G1, and the anchor is live). I am closing it. Usage week 83% (line about 89%, under it).

Note after A68 (04:09, auditor): two corrections to A68. (a) C90 was not ungated: it is a gated fresh start (paired gate), and so was C50 (z-gate, no descent in 18 iterations; #186). A68's recommendation (2) had already been tried twice, so I withdraw it. (b) Research proposes C92 instead (#304, runs/screens/C92-p479fresh/): C90's fresh-deck gated screen with only the pilot swapped to the 479 population's, 2 seeds, bands written first. It asks whether C91's shape lives in the pilot or in the 479 decks. It is a one-factor swap and the most direct next G1 test, so I support it. The precondition to check before launch: the 479 lineage was trained with no human prior. Awaiting 333-10's slot decision.

A69 · 2026-10-27 04:17 (from usage-latest t; Bash's permission check was erroring, so this was read with Grep/Read and gt_board was not run) · Ground truth: **new reading, C91-G3 (#305): C91's best 12 at 499 win 0.44 and 0.45 of decisive games against the lists** under the C49-sd 199 pilot, 2 seeds, against 0.11-0.22 for every fresh-deck screen. It is a measurement of the anchor, not an effect of a change: it starts warm from 479 and remains under G3's 0.5. Even so, it is the strongest G3 on record, and it agrees with C91's G1 (6.43). C92 (fresh decks with the 479 pilot, a one-factor swap) passed its human-free precondition (#306: random decks → pilot-v2 → lab main → resetcap). s1 has run since 04:15:16 (#307). s2 was refused at 04:15:26, presumably on the GPU/RAM gate: to check next audit. Count: 0 effects / 0 nulls / 2 not yet readable (C90 seed 2, C92).
- Long view: the work now runs a clean ablation on the ground truth (does the shape live in the pilot or in the decks?). That is the direction A54 asked for. If C92 reaches near C91's G1/G3 from fresh decks, the pilot carries the shape, and the rediscovery question becomes how the 479 pilot was made. Usage 5h 7% / week 83% (line about 89%, under it).

Note after A69 (about 04:39 from usage-latest t; auditor): **C90 at two seeds is null** (#308, #309). G3 C90 - C85 is +0.105 and +0.033, and Amendment 3 needs +0.08 on both. R-pilot's Trainer leg fails on both named sets, so the reading that "the deviation is the pilot's" is out. Count: 0 effects / 1 null / 1 not yet readable (C92). First measured G3 spread at 30 iterations: C85's seeds 0.011 apart, C90's 0.061. G1 leans to the gate (14.4 and 8.5 against 16.2 and 19.4, a two-seed gap of about 6, over the 3-point bar on both seeds). It was not banded, so under the null rule it is a lean, not an effect. It does agree with C91's banded R-repro: the gate matters for G1. The two together are worth one banded test: gated against ungated from fresh decks on G1, 2 seeds.

A70 · 2026-10-27 04:47 · Ground truth: nothing readable yet. C92 (fresh decks, 479 pilot) s1 is at it 17: 14.5 / 21.2 / 24.3, distance 14.2, mean5 13.9. That is in C90's range (mean5 13.9 / 10.9 at it 29 with the C49 pilot), so no sign yet that the 479 pilot carries the shape. Energy is still about +6. s2 launched at 04:35:33 after the GPU/RAM refusal cleared (it 4). C85-s2 ended at 04:36 (mean5 19.4). No new result. Count: 0 / 0 / 1 not yet readable (C92). Not stalled. A54 holds: the work is on G1. Usage 5h 7% / week 83% (line about 89%, under it).

A71 · 2026-10-27 05:16 · Ground truth: C92 s1 ended at 05:04. Final row: 13.2 / 22.5 / 24.3, distance 12.2, mean5 12.9, against C90 s1 (same chain, C49 pilot) at 13.9. That is a difference of 1.0, inside noise. s2 is at it 20 (distance 6.5, mean5 8.4, Trainers 25), against C90 s2's final 10.9. Not yet readable: C92 is read on the two-seed mean against its record's bands. Energy is still +3 to +6. No new result. Count: 0 / 0 / 1 not yet readable (C92). Flag: after C92 s2 nothing is queued ("seed 2s done"), so 2 of 3 slots are idle. That is not a stall, but the next banded G1 test (A69 note: gated against ungated from fresh decks) is not yet written. A54 holds. Usage 5h 7% / week 83% (line about 89%, under it).

Note after A71 (05:18, auditor): C93 is recorded with bands before launch (runs/screens/C93-gate-fresh-s34/record.md). It runs C85 and C90 unchanged at fresh seeds 3 and 4. R-gate if the seed-3-4 mean of (C90 - C85) G1 is -3 or less, null otherwise; prior null. Using new seeds keeps it independent of the seed-1-2 lean that suggested it, so it is a sound falsifiable test. It goes in the slot after C92 s2, pending 333-10.

A72 · 2026-10-27 05:33 · Ground truth: **new result: C92 at two seeds reads R-population, null (#312, #313).** The 479 pilot on fresh gated decks gives a two-seed G1 of 10.95 against C90's 11.45 (-0.50, inside 3), and G3 shows no gain. That matches the prior written before the run. Count: 0 effects / 1 null / 1 not yet readable (C93, s3 pair since 05:31).
- **Long view (a new result landed).** The thesis that the pilot carries the shape is now out twice (C90's R-pilot leg, and C92). C91's G1 of 6.4 lives in the 479 population (its decks and/or draft head; C92 doesn't separate the two). Antithesis to the next obvious step: that population was itself grown human-free from random decks over about 480 iterations (#306's lineage). Every fresh-deck screen tonight ran 30 iterations. Occam: the gap between fresh screens (about 11-14) and C91 (6.4) is most simply training length, not a missing mechanism. The 30-iteration screens can't test rediscovery, because the human-free lineage that got closest needed hundreds of iterations.
- **So the ground-truth question is now:** does a long gated run from random decks reach about 6 on its own, and does Energy then fall from +3.5? It is a run of hours, not a 5-minute one, so it needs a timed pilot and stop bands. The cheaper first check: read the 479 lineage's own G1 trajectory from its logs (does G1 descend steadily with iterations?) before spending GPU. C93 still runs as banded.
- Usage 5h 8% / week 83% (line about 89%, under it).

Note after A72 (05:34, auditor, on #314): my A72 claim that "training length explains it" is partly wrong. The 479 lineage (ungated, human-free) reached G1 at or below 8 once, near iteration 290 (25-iteration mean 12.5 at 275-299). It held about 85 iterations and then collapsed back to 35 by 425-449. That is n = 1, one lineage. Dialectic resolved: length can find a near-list state human-free, but without the gate it doesn't keep it, and the gate is the only thing so far that has held one (C47, C91). The two options are with 333-10 for Evan: (a) a long gated run from random decks, 300+ iterations, about 6.5 h+; (b) a gated fork at about 290. Auditor's view: (b) tests stability, not rediscovery. A middle option is a gated fork at about 275 (distance about 27, before the first near-list row). It tests both descent and holding for a few hours, not 6.5. Per Evan's short-experiments rule, time a pilot first and write stop bands, whichever runs.

A73 · 2026-10-27 05:47 · Ground truth: nothing readable. C93 s3 pair is at it 8: C85-s3 distance 6.0 / mean5 10.7, C90-s3 11.8 / 11.1. Too early, and the noise is large. C93 is read only on the s3-4 mean of (C90 - C85). No new result. Count: 0 / 0 / 1 not yet readable (C93). #315 sizes the fork points for a gated "find the lists" test: seg_0240 (distance about 36) or seg_0280 (about 18-21). Proposed, not yet run. Not stalled. A54 holds: the work and its next test are on G1. Usage 5h 10% / week 84% (line about 89%, under it).
- Caveat from #315, by working rule 9: the 479 lineage's drop to 6 at iteration 290 coincides with the deckcross adoption. Part of that "first approach" may be a change in the judge (the measurement), not in the decks. A fork test needs G1 measured the same way at the fork and after it.

A74 · 2026-10-27 06:17 · Ground truth: nothing readable. C93 s3 pair near its end: C90-s3 at it 27 has distance 7.5 / mean5 9.5 (13.5 / 24.5 / 22.0); C85-s3 at it 25 has 17.0 / mean5 10.4. The mean5 gap is -0.9 so far, under R-gate's -3, and it is read only on the s3-4 mean. No new result. Count: 0 / 0 / 1 not yet readable (C93). Not stalled. A54 holds. Usage 5h 10% / week 84% (line about 89%, under it).

A75 · 2026-10-27 06:47 · Ground truth: C93 s3 pair ended. C90-s3 mean5 9.0 (last row 9.2), C85-s3 mean5 17.2 (last 11.5). (C90 - C85) at s3 is -8.2 on mean5 and -2.3 on the last row; the record's G1 definition decides which counts. s4 pair since 06:22 (it 12-13: C90 14.5, C85 9.3, early). R-gate is read only on the s3-4 mean (at or below -3). No new result. Count: 0 / 0 / 1 not yet readable (C93). Not stalled. A54 holds. Usage 5h 10% / week 84% (line about 89%, under it).
- Clarification: the audits header defines the G1 bar on the mean-of-5 distance, so s3's gap counts as -8.2. One seed. s4 decides.

A76 · 2026-10-27 07:17 · Ground truth: **new result: C93 done (07:16). By my reading of gt_board it reads R-gate, the first effect under the null rule since these audits began.** Mean5 G1, C90 (paired gate) against C85 (ungated), 30 iterations from fresh decks: s3 9.0 against 17.2 (-8.2), s4 8.7 against 18.3 (-9.6). The s3-4 mean is -8.9 against the pre-written bar of -3 or less. All three conditions hold: it is about 4x G1's seed noise of about 2, it holds on both new seeds, and it was banded before launch with a null prior. Seeds 1-2 (unbanded) lean the same way (-1.8, -10.9), 3 of 4 seeds clearly beyond. Count: **1 effect** / 0 nulls / 0 not yet readable. This is my reading; research's formal read against the record is pending.
- **What it is and isn't.** The gated arm's best 12 sit about 13 / 23.6 / 23.4: Energy still +5.4, Trainers -4.4, distance about 8.7 (C91's anchor is 6.4). So the gate is an effect on G1, and it mostly stops the ungated drift to Pokemon-heavy decks (C85: 17-20 Pokemon). It is not rediscovery: the Energy lean, the original minimum, is untouched.
- **Long view.** The 10-24 cleanup removing the gate cost about 9 points of G1 on every ungated screen since. That vindicates A54's antithesis and A55's pipeline call. Thesis for the next step: selection with a significance gate is necessary but not sufficient. The Energy +3.5 to +5 persists in every gated run, warm (C91) or fresh. Occam: the gate is now the base, every drafting arm is gated, and the open problem is again the Energy lean. Per C90 and C92 that is not the pilot's prompt-answer skill and not the pilot swap. That leaves what the draft is rewarded for (its selection signal or the game value it reads), plus the fork test for holding (#315). Usage week 84% (line about 89%, under it); the 5-hour window reset at 07:10.

Note after A76 (07:17, auditor): **C93 R-gate confirmed formally (#316), no longer provisional: the first effect.** s3-4 mean -8.85 (aa_window), each seed below -3. All four seeds: -7.60, Welch CI [-11.87, -3.33], p 0.007. G3 doesn't move, and Energy stays high (+1 to +3 on the population median, about +5 in the best 12). Next step (gate as the base, then what the draft is rewarded for) is with 333-10 as item 4 for Evan.

A77 · 2026-10-27 07:46 · Ground truth: nothing moved since A76. C93 R-gate is the standing effect, G3 has no gain, Energy is still +5 in the best 12. No new result. Count: 0 / 0 / 0. The GPU is idle on purpose, left free for Evan's morning (#317), so this is not a stall. The next steps (gate as base; the draft's reward; the #315 fork) wait on Evan's decisions via 333-10. A54 holds. Usage 5h 1% / week 84% (the week resets at about 09:00).

A78 · 2026-10-27 08:16 · Ground truth: nothing moved; no new result; 0 / 0 / 0. The GPU is idle for Evan's morning (#317), so not a stall. Next steps wait on Evan. A54 holds. Usage 5h 1% / week 84% (resets about 09:00).

## Dialectic audits (Evan, 2026-10-27 about 07:25 via 333-10: "request research whenever nothing moves"; each entry: ground truth, thesis, antithesis, evidence, synthesis; job 15eaa07f at :13/:43)

A79 · 2026-10-27 08:40 · first dialectic audit
1. **Ground truth.** Best G1 on today's code: C91 (warm from 479, gated) two-seed 6.43. Fresh gated decks (C93/C90, 4 seeds): mean5 8.7-14.4, best 12 about 13 / 23.6 / 23.4, so Energy +5 and Trainers -4. G3: C91's best 12 win 0.44 / 0.45 against the lists. Fresh populations win 0.14 / 0.16 gated against 0.10 / 0.17 ungated (vs_lists, s3/s4), no gain. Nothing moved since C93 (07:16).
2. **Thesis (the team's):** the draft drifted because its selection read game noise; the gate fixes the drift, and the remaining Energy lean comes from what the draft is rewarded for. Running: nothing. Item 4 ("gate as the base, then the draft's reward") waits on Evan.
3. **Antithesis (untested by the queue):** the draft is faithful, and Energy-heavy decks really do win more under this pilot on engine K. ar/'s own start says so: M = 0.474 < 0.5, so the human lists lose to their Energy-filled copies under the C49-sd pilot. Then no draft reward can recover the lists: the deviation is in play strength with Trainers (or in how the engine implements Trainers), not in drafting.
4. **Evidence.** For the thesis: C93 R-gate (4 seeds, CI [-11.9, -3.3]) shows selection noise mattered for G1. But the gate left Energy and G3 unchanged, which is what the antithesis predicts. For the antithesis: M < 0.5 at start, measured over many A/A seeds (0.450-0.488), and C91's Energy-heavy best 12 beat the lists 0.44 / 0.45. Against it: the four pilot-target arms (p23-C89) and the pilot swap (C92) were null. But they changed how the pilot learns, not how strongly it plays at test time, so they don't test it directly.
5. **Synthesis: the cheapest discriminating experiment.** Evaluation only, no training: re-measure M (the lists against their Energy-filled copies) with the same C49-sd pilot plus test-time search (the existing j-search or R-search path; deeper rollouts at Trainer decisions). If M rises above 0.5 with search, the pilot's play strength is the bottleneck, and draft-reward work can't fix the lean. If M stays under 0.5 even with search, suspect the engine's Trainer implementations (check them against notes/sts-2000-engine-check.md) or the round rule. Either way it is about an hour of GPU and no human prior (the lists are evaluation only). Not queued.
RESEARCH CALL: Is the Energy lean a drafting fault or a play/engine fault? Test: M under the C49-sd pilot with test-time search against without, 2 seeds, bands first (search lifts M by at least 0.03 and above 0.5 → play; otherwise engine/rules). No metric has moved since 07:16, and nothing is queued. Usage 5h 6% / week 84% (line about 91% at the reset near 09:00, under it).

A80 · 2026-10-27 08:44 · (1) Ground truth: nothing moved. Best G1 C91 6.43; fresh gated about 13 / 23.6 / 23.4, mean5 8.7-14.4; G3 best 12 0.44 / 0.45 (C91), fresh populations 0.10-0.17. No new results. (2) Thesis: unchanged (gate fixed the drift; the Energy lean is in the draft's reward or the pilot's Trainer skill). New work: C95 (written 08:44), an offline Q head over prompt answers, scored against a C94 oracle. (3) Antithesis: as in A79, the draft is faithful, and Energy really wins under this pilot (M 0.474 < 0.5). (4) Evidence: nothing new. **Flag, off focus:** C95 reopens the prompt-answer value line that #296 closed after 4 nulls (p23, C82, C88, C89). It is offline and cheap (about 10 minutes a candidate), and its oracle is evaluation-only (row 60), so it is within the rules. But nothing in the null record gives a reason to expect a different outcome, and it doesn't touch G1/G3. (5) Synthesis: A79's search-M test. runs/probe/C96-search-M/ exists but is empty (no record yet), so it is not yet queued.
RESEARCH CALL: still A79's question (drafting fault, or play/engine fault?). Write and run C96 (M with test-time search against without, same pilot, 2 seeds, bands first) ahead of C95. No metric has moved in the last 2 hours (last: C93 at 07:16). Usage 5h 9% / week 85% (line about 91.5%, under it; resets about 09:00).
