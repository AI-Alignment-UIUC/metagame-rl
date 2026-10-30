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

Note after A80 (08:45, auditor): two corrections. (a) C96's record exists, bands first (R-play: lift at least +0.03 and M_search at least 0.50; between; R-not-play: lift under 0.03; prior between). It is being run beside the C94 oracle build, ahead of C95. My "empty folder" came from a listing that missed it, and the RESEARCH CALL's experiment is now queued. (b) C95 is Evan's own request (about 07:25: "research multiple ways of learning the value head ... against the oracle"), so it goes first under his ideas-first rule. It differs in kind from the 4 nulls: offline, scored directly against an oracle, with controls that should reproduce the nulls. Nothing returns to training without a 2-seed band. I withdraw the "off focus" flag.

A81 · 2026-10-27 09:14 · (1) Ground truth: nothing moved. Best G1 C91 6.43; fresh gated best 12 about 13 / 23.6 / 23.4; G3 best 0.44 / 0.45, fresh 0.10-0.17. (2) Thesis: the Energy lean lives in the pilot's value of Trainer answers. Running on it: C94 oracle build (batch 4 of the m-256 set, about 09:40) and C95 harness (smoke run 09:00). (3) Antithesis: the draft is faithful, and Energy wins under this pilot because of play strength or the engine's Trainer rules. Running on it: C96. (4) Evidence: C96 stage 1 greedy M = 0.4325 ± 0.0199 (seed 1, 96 pairs, 24 lists, 8 games a pair). That again puts the lists below their Energy-filled copies under C49-sd: M < 0.5 by about 3.4 SE. The search half (4:4:crn) has written nothing since 08:59 (15 minutes). Not yet stalled; check next audit. No banded result yet. (5) Synthesis: C96 is the discriminator, and it is running.
RESEARCH CALL (2-hour rule: no metric has moved since C93 at 07:16): the next question if C96 reads "between" or R-not-play: is engine K's Trainer handling right? Cheapest test, CPU only, meanwhile: replay the named five (Computer Search, Super Energy Removal, Energy Removal, Energy Retrieval, Gust of Wind) against the card texts in notes/sts-2000-engine-check.md, and measure M with those five Trainers removed from both sides. If M is about 0.5 without them, the engine's or the pilot's use of those cards is the fault. Usage 5h 21% / week 1% (reset at 09:00, under its line).

Note after A81 (09:16, auditor): A81's engine half was already answered. #233 live-tested every pool Trainer, and the named five resolve as printed. #235 fixed the faults found, and C67 (#236) found the lists' Trainer prices unmoved by the fixes (+0.005 ± 0.006). My pointer to sts-2000-engine-check.md was wrong: it checks pool coverage, not card behaviour. Working rule 6 applies to me too: check earlier attempts first. The per-card half is new and queued as C97 (runs/probe/C97-card-prices/record.md, bands first, about 10 minutes): each named card alone turned into Energy on the 24 lists. A card carries the deficit at p + 2 SE < 0.50, and C67's groups rerun as reproduction checks. With the engine verified, a card that carries the deficit points at play.

A82 · 2026-10-27 09:44
1. **Ground truth.** G1 unchanged: C91 6.43, fresh gated about 13 / 23.6 / 23.4. **G3 corrected (#325-#327, a best_decks bug voided every G3 since 10-24):** fresh-deck screens 0.18-0.28. C91's best 12 beat the lists 0.57 while carrying +3 to +4.5 Energy. G3's 0.5 is met by Energy-heavy decks, so under the C49-sd pilot G3 can't tell "rediscovered" from "exploits the pilot". G3 needs a qualified pilot (the header's G3 says so), and one under which the lists lose to their Energy copies (M 0.43) isn't qualified.
2. **Thesis.** The Energy lean is the pilot's under-valuation of Trainers, learnable through a better value head. Running: C95 stage 1a/1b against the C94 oracle (R 0.503 on the named five, usable "just").
3. **Antithesis (untested).** C97 localises the deficit to one card: **Computer Search alone carries it (p 0.447, CI [0.425, 0.470], bands first, 1 seed; the controls reproduce C67).** Energy Removal holds its slot (0.536). CS is the one staple whose value is pure consistency (discard 2, fetch any card) and pays off only over a long game. The rival: the game format undervalues consistency, not the pilot. round_turns [20, 45] (the round rule) ends or scores games early, so a card that trades 2 cards now for the right card later loses to a raw Energy. A second rival in the same place: CS's fetch is a multi-card pick (#233: picks "in an order the pilot cannot see", fixed in #235). Does the pilot see the deck's contents at the search prompt?
4. **Evidence.** C96 stage 1: test-time search lifts M by +0.002 ± 0.025. Underpowered, so there is no evidence either way on play strength. C95 stage 1a: every rho CI includes 0, so nothing learns the signal yet; that is a null for the thesis so far. C97: 1 seed, banded, so a localisation, not yet an effect.
5. **Synthesis: the cheapest discriminator.** Re-price Computer Search alone (C97's command, about 10 minutes, 2 seeds) under (a) the round rule as now, (b) games played to completion (no turn cap), and (c) CS's fetch picked by MC rollouts (C94's oracle machinery; evaluation only, never trained on, row 60). If (b) lifts p above 0.5, the format is the fault. If only (c) does, the pilot's fetch choice is. If neither does, CS is truly weak in this engine. Also check, once, that the search prompt shows the pilot the deck's contents. Not queued.
RESEARCH CALL: why does Computer Search price below an Energy: the round rule, the pilot's fetch choice, or an observation gap? Run C97's CS-only price under no-turn-cap and MC-fetch, 2 seeds, bands first. No G1 metric has moved since 07:16. Usage 5h 30% / week 2% (under both lines).

Note after A82 (09:47, auditor): A82's call is answered by C98 (runs/probe/C98-cs-why/record.md, #332, about 30 minutes, bands first). Prior data cited: (a) clock: C59 untimed games price the search group lower (0.375 against 0.412 timed), against my R-clock at group level. C98 tests Computer Search alone. (b) choice: C73's oracle answers lift the search group +0.063 (SE 0.013). (c) view: #233's pick order is fixed, and C98 dumps the search prompt once. Research's prior: clock refuted, choice partial, view no. My G3 caveat was added to C91's record. The discriminator is queued.

NOTE, FOCUS CHANGE (about 10:08, Evan rows 89-91, relayed by 333-10 at 10:04; read at every audit until replaced): the focus is to replace card IDs with cross-attention over content-based card embeddings, so the pilot can target the full deck (Computer Search) and identify cards correctly. All other experiments are paused (C95, C96, C98 and the rest). A pause is not a stall; work drifting back to them is drift. Audit against four checks: (i) is the id question settled (global or deck-relative)? (ii) is the card content table built? (iii) has the design landed? (iv) is a 30-minute test running? The ground truth still leads each entry.

A83 · 2026-10-27 10:15 · first audit on the card-embedding focus
1. **Ground truth.** Not moved: G1 C91 6.43, fresh gated about 13 / 23.6 / 23.4; G3 (corrected) fresh 0.18-0.28, C91 0.57 (with the A82 caveat). **New, replicated: Computer Search priced against Energy on the lists is 0.4474 (seed 91) and 0.4426 (seed 2), both CIs under 0.5, banded (C97/C98).** The deficit sits in one card on 2 seeds. C98 untimed: 0.402 / 0.398, so R-clock is refuted on 2 seeds.
2. **Thesis (Evan, rows 89-91):** the pilot can't identify or target the deck's cards because IDs differ across decks. Fix: cross-attention over content-based card embeddings. Focus checklist: (i) id question **settled: global** (#337 data, #339 code, env/tokens.js:72-89, 303); (ii) content table **built already** (notes/data/cards/pool.json, 277 cards, plus MiniLM text embeddings, used by the pilot's card_emb at rl/token_model.py:395-400); (iii) design **not landed** (333-10's design phase, "within the hour"); (iv) 30-minute test **not running** (nothing runs, #339).
3. **Antithesis.** The premise of the focus doesn't hold in the code. IDs are global, and every option row already carries the card's content embedding. MY_UNSEEN already gives the remaining deck with copy counts (#340), and slot targets are bound to their board token. The one link missing for deck picks (an option reading the encoder state of its card) is cand_latent, tested as C87: null. So identification probably isn't the bottleneck. CS's fetch choice is (C73: oracle answers lift the search group +0.063), or CS is simply weak for this pilot.
4. **Evidence.** For the antithesis: #337, #339, #340 (code facts) and C87's null. For the thesis: #339's three real gaps (a per-id residual that can memorise, no copy count on options, no card ref on slot picks). Plausible, but none has been shown to matter. C95 stage 2: no value-head candidate meets its band.
5. **Synthesis: the cheapest discriminator, and it's within the focus because it sizes the design's possible payoff.** Run C98's two remaining prompt-oracle runs (CS priced when its fetch and discard are chosen by MC rollouts; evaluation only, row 60), minutes, bands already written. If the oracle-chosen CS is at or above 0.5, better card targeting can pay, so build the design. If it stays under 0.5, no targeting architecture can fix CS, and the design would be work with no ground-truth payoff. Not queued: paused by the focus.
RESEARCH CALL: will a better card-targeting architecture pay on the ground truth? Run C98's prompt-oracle runs (minutes) before building, and bring #339's finding to Evan: the IDs are already global and content-embedded, which contradicts row 90's premise. Usage 5h 45% / week 4% (under both lines; 5h is the one to watch).

Note after A83 (10:15, auditor): research agrees. A go for C98 condition 3 (about 10-15 minutes, evaluation only, bands in the record) has been requested from 333-10, ahead of the design build. Caveat for reading it: the oracle S tries each option on 4 re-dealt copies to the end of the turn and scores by the pilot's own value. An S null bounds only choices as good as S's (a one-turn horizon, scored by the pilot's value), not every targeting. A null would be strong evidence against the design's payoff, but not proof.

NOTE, FOCUS UPDATE (about 10:30, Evan row 95, relayed by 333-10 at 10:32; replaces the 10:08 focus note; read at every audit until replaced): drafting pauses. The pilot's architecture is developed on a single-deck bench of C91's best self-discovered decks (2-4 Computer Search each) until it plays Trainers well. Bench measures: (a) the bench deck's Trainer prices (target at least 0.5); (b) target skill against a bench oracle; (c) a card-value probe of the state representation; (d) win rates. Arms are 30 minutes. Audit order: the ground truth first (it won't move while drafting is paused, so say so in one clause), then the bench measures against each arm's bands. Drafting work counts as drift unless Evan approves it. Bench decks are self-discovered (C91), so no human prior; the lists stay evaluation only.

A84 · 2026-10-27 10:44 · bench focus (row 95)
1. **Ground truth.** Not moved, and it won't while drafting is paused: G1 C91 6.43, fresh gated about 13 / 23.6 / 23.4; G3 (corrected) 0.18-0.28 fresh, 0.57 C91 (A82 caveat). **New: C98 condition 3 (#341, #342), oracle-chosen answers lift Computer Search's price by +0.050 on 2 seeds, to about 0.46, still under 0.5: R-choice partial**, banded. Better choices recover about half of CS's deficit (0.44 → 0.46 against 0.5).
2. **Thesis (Evan, rows 94-95):** CS is only as good as the gap between the card fetched and the two discarded, at that moment. The pilot can't judge it because its state representation doesn't value cards well. Develop the architecture on a bench until it plays Trainers well. Running: bench arm 0 (readouts 1 and 4 plus the CS differential), then P2 (key 1 opened from zero, picks only), then P1 (content-keyed cross-attention) (#348, #349). C99 (a CS timing oracle) is recorded.
3. **Antithesis.** Even perfect per-prompt choices leave CS under an Energy (0.46 with the oracle). The rest of the deficit isn't in which card it fetches but in whether a 2-card discard is ever worth it under this pilot's game plan, which is the value of the follow-through. That is C99's question, and the architecture arms don't test it.
4. **Evidence.** For the thesis: R-choice partial, +0.050, real on 2 seeds. For the antithesis: the oracle ceiling is still 0.46, and that oracle is one-turn and scored by the pilot's value (research's caveat). Bench arms: none read yet.
5. **Synthesis.** Run C99 (the timing oracle with follow-through) next to bench arm 0. It bounds what any architecture could gain on CS: if timing plus choice reach 0.5, the bench's target is reachable; if not, the bench target of 0.5 for CS may not be reachable on this engine and pilot family. Recorded, not running.
- **Flag, human prior (rule check):** #346/#347 put human lists into training: the bench pilot practises on human lists 3, 1, 21, 2 (Evan, about 10:35-10:38). It is quarantined: "bench pilots never seed drafting or ar/; the architecture retrains human-free when drafting resumes" (#346). That keeps the self-discovery rule only if no weights, hyperparameters tuned to those decks, or data cross into the self-play line. Audits will check that at the hand-back. Evan's explicit call, so it is recorded, not a violation.
- **Flag, usage:** 5h at 63% (line 75%), resets about 12:10 (#349 trimmed the plan for it). Week 7%.
RESEARCH CALL: can any Computer Search play reach 0.5 under this pilot family? Run C99 (timing with follow-through) beside bench arm 0. No ground-truth metric has moved in 2 hours.

Note after A84 (10:45, auditor, on #350): (1) C99 moves onto the bench's 4 P lists: Computer Search alone turned into Energy, arms G / S / T / ST, seeds 91 and 2. ST (oracle choice plus oracle timing) answers A84's call. If ST - 2 SE < 0.50 pooled, CS's bench goal is marked unreachable by choice and timing under this pilot family. It is sequenced inside the usage window. (2) BENCH Amendment 3 extends the quarantine: no weights, initialisations, distillation targets, bench-tuned hyperparameters or data cross into drafting or ar/. Only architecture code and pre-bench defaults cross, retrained human-free. Any exception is Evan's. The human-prior flag is closed, to be checked at the hand-back.

A85 · 2026-10-27 11:14 · (1) Ground truth: not moved (drafting paused). (2-4) Bench: new calibration (#352). The start pilot prices the 4 practice lists' Trainers at 0.501 pooled, but Item Finder 0.435 and Computer Search 0.467 sit clearly under an Energy, so the per-card goal fails at the start on those two. Arm 0 s1 (30 minutes, since 10:45) is just finishing; no arm read yet. That is a second card (Item Finder) with the same consistency-for-cards profile as CS. It fits A84's antithesis (a discard cost the pilot can't recoup) at least as well as the identity thesis. (5) C99 (ST arm) is still not run: queued behind arm 0 and O_B. **Flag, usage: 5h at 72%, just under its 75% line, resets about 12:10.** Nothing new should start before the reset unless it fits. Week 8%. No RESEARCH CALL: C99 is queued, and the research rounds would spend the 5h window.

A86 · 2026-10-27 11:44 · Ground truth: not moved (drafting paused). Bench: arm 0 s1's evaluation ran from 11:19 and isn't in the log yet; s2 is training (it 16, writing at 11:43), not stalled. No new progress-log entry since #352. C99 still queued. No new result. Usage 5h 72% (under 75%, resets about 12:10) / week 8%. RESEARCH CALL deferred to the 12:10 reset (2-hour rule: no metric has moved). The question stays A84's: can any Computer Search play reach 0.5? Test: C99 ST.

A87 · 2026-10-27 12:15 · bench
1. **Ground truth.** Not moved (drafting paused): G1 C91 6.43, fresh gated about 13 / 23.6 / 23.4; G3 0.18-0.28 fresh.
2. **Thesis:** the pilot's representation can't value its Trainers (identity and differential, rows 94-95). Fix it on the bench (P2, then P1).
3. **Antithesis now sharpened by arm 0:** stronger play doesn't buy Trainer value. **Arm 0 (plain PPO, 2 seeds × 30 minutes, #353/#354): the mirror against the start pilot is 0.636 / 0.594, clearly stronger on both seeds, but the Trainer prices are null (pooled 0.520 / 0.505 against 0.501, +0.012 inside noise).** So A79's rival in its simple form ("Trainers lose because play is weak") is out: PPO gets stronger by routes that don't run through Trainers. What remains to tell apart: (a) the representation can't express a Trainer's value, so the architecture is the fix (thesis); (b) the objective never rewards it: on this pilot's win paths a 2-card discard doesn't pay, whatever the representation, so even perfect play leaves CS and Item Finder under an Energy.
4. **Evidence.** For (a): R-choice partial (+0.050 with oracle choices). For (b): the oracle ceiling is 0.46 for CS, and arm 0's strength gain left the prices flat. Both readings are banded, on 2 seeds.
5. **Synthesis.** C99 ST (oracle choice plus oracle timing, CS alone, 2 seeds) is still the discriminator: under 0.5 there means (b), and the bench's CS goal is out of reach for any architecture under this pilot family. It is queued behind Amendment 4's smoke run and not started. The 5-hour window has just reset, so it fits now.
RESEARCH CALL (2-hour rule; deferred from A86 for usage): run C99 ST before P2/P1's builds take the GPU. Its answer decides whether the architecture arms can reach their target at all. Usage: 5h reset at 12:10 (not in the file yet) / week 8%.

Note after A87 (12:16, auditor): A87's call accepted. C99's hook and P2 are built on CPU while O_B finishes (about 12:44). Then C99 runs first on the GPU (bench, start pilot, about 10-20 minutes), then P2's arm. Decision rule: ST - 2 SE at or above 0.50 pooled → (a), the play exists, so the representation arms have a target. ST under 0.50 → (b) for Computer Search, so P2/P1 are read on the other Trainers and their mechanism gates, not on CS's price. The rule was written before C99 runs. One wording gap to watch: ST between 0.50 and 0.50 + 2 SE fits neither branch, so read it as (b).

Note (12:16, auditor): C99 Amendment 2 is written before the run (checked in the record). Three bands on pooled ST: reached (a) if ST - 2 SE is at least 0.50; not reached (b) if ST + 2 SE < 0.50; between otherwise (no target claim, and P2/P1 are read as in (b)). The gap is closed.

A88 · 2026-10-27 12:44 · Ground truth: not moved (drafting paused). Bench: CS re-priced at 256 games a pair (#355, #356): 0.441 start, 0.464 / 0.453 arm 0 (+0.018 mean, under the about-0.03 bar), null and consistent with A87. C99 (the discriminator) is running: bench files are being written at 12:43. P2 is built. Flag: O_B crashed at 12:22 and is requeued with per-batch saving. That is not a stall. No new result. Usage 5h 4% / week 10% (both under). RESEARCH CALL (2-hour rule only): no new round is needed, because the discriminator (C99 ST) is in flight. Read it against Amendment 2's three bands when it lands.

A89 · 2026-10-27 13:14 · bench
1. **Ground truth.** Not moved (drafting paused).
2. **Thesis:** the representation limits Trainer value. P2 (key 1 from zero, picks only) started at 13:13 (arm-p2-s1); P1 is building.
3. **Antithesis:** the deficit is built into the pilot family's win paths. **C99 (#357, #358, banded by Amendment 2): oracle choice plus timing puts Computer Search at about 0.50-0.54 for three pilots, every CI spanning 0.50, so "between": no target claim.** Timing adds nothing (T - G about 0). Choice alone carries the lift. Arm 0 already plays CS selectively, with same-turn follow-through 92-98%, yet its price stays at an Energy.
4. **Evidence.** (b) is not established, since oracle choice brings CS to about 0.5, so a near-even CS play exists. (a) gains a little: the gap is in which cards are fetched or discarded, not in when CS is played. But a "between" is no target claim, so P2/P1 are read on the other Trainers and their mechanism gates, as written. The simplest reading: CS's ceiling under this pilot family is about an Energy, and the realistic gain is +0.05 (0.44 → 0.50). A small bench target even if P2/P1 work.
5. **Synthesis.** P2 is the queued test of (a): content keys for picks. Under the rule, read it on Item Finder (0.435, the bench's other clear deficit) and the mechanism gate, not on CS. Running.
- Long view: the bench is hours old, and its ceiling for CS is now known (about 0.50). It's worth asking Evan whether the bench target "Trainer prices >= 0.5" should be per-card or pooled. Pooled is already 0.50-0.52 at the start (#352), so the bench may be chasing a ceiling. No RESEARCH CALL: C99 read inside 2 hours, and P2 is the next discriminator, already running. Usage 5h 13% / week 12% (under).

NOTE, BENCH TARGET (Evan, about 13:20, row 98: "per card sure"; relayed by 333-10 at 13:29): the bench target is per card. Every Trainer in the practice lists must price at least 0.5 against a basic Energy, judged inside that card's noise band. A pooled mean doesn't count. Audits read per-card prices. Failing today: Item Finder (0.435) and Computer Search (about 0.44-0.46). From C99, CS's ceiling with oracle choices is about 0.50-0.54 ("between"), so reaching it needs near-oracle choices.

A90 · 2026-10-27 13:44 · bench, per card (row 98)
1. **Ground truth.** Not moved (drafting paused). Bench per card: Item Finder 0.435 and Computer Search 0.44-0.46 still fail. P2 s1: CS 0.451 (arm 0 0.464). No card has moved.
2. **Thesis:** the pilot can't tell a Trainer's worth because its representation doesn't separate them. **New support (#363-#368): content embeddings put 40 of 42 Trainers on one structural feature row. CS and Item Finder sit at cosine 0.976-0.99 under every centring.** Running: P1 (content-keyed cross-attention, gate missed, runs as built), then P2 s2.
3. **Antithesis (untested by the queue): the information is already there, and the learning signal is too weak.** C95 (#333): a ridge probe on today's option vectors already recovers the per-answer value (rho 0.33-0.45 on CS and Gust, CIs above 0). The per-id residual already separates CS from Item Finder whatever their content. P2's path is near-dead (fetch ratio 0.019). A pick's effect is about 0.02, and CRN discordance d = 0.20 means about 8,000 paired samples per 0.02 gap (#319). A 30-minute arm sees far fewer CS and Item Finder picks than that. Then no architecture can learn it at this budget; only more signal per pick can.
4. **Evidence.** For the thesis: the near-identical content (a design fact, not an outcome). For the antithesis: C95's linear capacity, P2 s1 null without harm (0.501 against arm 0), and C87 null earlier. The bench arms so far are 0 effects / 2 nulls (arm 0 on prices, P2 s1).
5. **Synthesis: the cheapest discriminator costs nothing.** Count the CS and Item Finder picks one 30-minute arm actually trains on (from arm 0's or P2's logs) against the roughly 8,000 paired samples a 0.02 gap needs. If arms see under about 10% of that, every 30-minute architecture arm is underpowered by construction, and the bench needs a denser signal (paired re-deals at the pick, as the oracle does, used as training targets from the pilot's own playouts, row 83) before architecture can show anything. Not queued.
- **Flag, process:** P2 s2 died of a CUDA OOM at 13:28 beside P1's build tests (#362, "my sequencing"). The row-73 hold should have stopped that launch. Rerun queued.
RESEARCH CALL: can a 30-minute arm learn a 0.02-per-pick signal at all? Count trained picks per arm against the roughly 8,000 paired samples needed (zero GPU), before P1's verdict is read as an architecture result. Usage 5h 27% / week 14% (under).

Note after A90 (13:46, auditor, on #369): A90 confirmed, with estimated numbers (training logs do not count picks per Trainer). A 30-minute arm trains on about 8,000-15,000 Computer Search fetches, against about 290k visits for PPO's single-visit sign: 20-40x short. **The outcome readouts of P2 and P1 are underpowered by construction, so their nulls say nothing about architecture. Only their mechanism readouts are readable.** Next: exact per-Trainer pick counts in bench_train; a dense-signal arm (a ridge value over answers from the pilot's own paired re-deals, row 83) is proposed to Evan via 333-10 and needs its own record. Row 73: the OOM is admitted as a hold miss, and the rule is now no GPU work beside an arm.

NOTE, NO HUMAN GATE (Evan 14:03, "Keep experimenting for awhile, don't wait on my approval right now", relayed by 333-10 at 14:03): the agents run the bench program without Evan's approvals. That includes runs over 30 minutes when a record justifies them, in 30-minute stages. These audits are now the main check. At every audit, flag: (a) any run without bands written before launch; (b) any stage that ran past its stop rule; (c) drift off the bench focus (per-card Trainer prices; drafting stays paused); (d) usage over its caps (5h at or under 75%, the week's line); (e) row-73 holds and the bench quarantine (BENCH Amendment 3). Keep making RESEARCH CALLs when nothing moves. Still out of bounds without Evan: changes to the training rules, human priors outside the quarantine, copying oracle answers (row 60).

A91 · 2026-10-27 14:14 · bench, no human gate
1. **Ground truth.** Not moved (drafting paused). Per card: Item Finder 0.435 and CS about 0.45 still fail. No bench arm has read since P2 s1.
2. **Thesis (now the team's, after A90):** the rare Trainer decisions get too little training signal per pick (20-40x short), so architecture can't show until the signal is denser. Queued: P4 (#370, #371), a ridge value over prompt answers from the pilot's own paired re-deals (row 83) plus a prompt-advantage swap, on top of the binding arm. Its record is banded, with a kill rule (branching over 75%, errors over 1%, KL > 0.05 for 2 iterations) and chained 30-minute segments after a 2-seed mechanism pass. Plus research round 4 (deep research on multiplying rare-decision signal, 14:07).
3. **Antithesis:** a denser signal makes the pilot learn the oracle's one-turn preference, and that preference only gets CS to about 0.50 (C99). So P4 can at best bring CS level with an Energy, maybe not above. Item Finder has no oracle ceiling measured yet. If Item Finder's ceiling is also about 0.5, the per-card goal is near the edge of what this family can do.
4. **Evidence.** C99 ST (between, 0.50-0.54) bounds CS. Item Finder's ceiling: none. Nothing new since A90.
5. **Synthesis.** Measure Item Finder's oracle ceiling (C99's S arm on Item Finder alone, about 15 minutes, evaluation only) before P4's long segments. It tells whether P4's target is reachable for the second failing card. Not queued.
- **Checks (no human gate):** bands first: P4 yes. Stop rules: none breached. Focus: on the bench. Row 73: GPU is O_B only. P1 is built but not launched; P2 s2 is queued after O_B. No stall.
- **Flag, usage trajectory:** 5h is 42% at 14:14, up from 27% at 13:44 (+15 points in 30 minutes). At that pace it crosses 75% by about 15:20, two hours before its 17:10 reset. The hourly deep-research rounds (row 99) are the likely driver. Hold them, or keep them lean, until the window resets. **Week 15% against a line of about 3% (92% × 5.2 h / 168 h): well over.** Under Evan's rule, hold fan-outs (the deep-research subagents) while the week is ahead of its share elapsed.
RESEARCH CALL: Item Finder's oracle ceiling (C99 S on Item Finder alone) before P4's long run. No metric has moved in 2 hours.

Note after A91 (14:15, auditor, on #373): (1) Item Finder's ceiling is queued as C99 Amendment 3: G/S on Item Finder alone, lists 3/1/2, seeds 91 and 2, the start pilot, the same three bands, before P4's long segments. (2) Usage: the 14:07 round (4 researchers) finishes; no fan-outs until about 17:10; the 15:08 round is skipped if 5h is over 75%, otherwise one researcher. **Open flag:** the week rule is not a 5h rule. At 17:10 the week will be about 17% or more against a line of about 4.6% (92% × 8.2 h / 168 h). It stays ahead for about 1.5 days at today's pace, so fan-outs stay held past 17:10 unless Evan says otherwise.

Note (14:16, auditor): research has adopted working rule 18 in its handover. While the week is ahead of its elapsed share, each hourly round uses one researcher plus the report writer, after 17:10 too, until Evan says otherwise. A round is skipped when 5h is over 60%. The audits check this each time.

A92 · 2026-10-27 14:45 · bench
1. **Ground truth.** Not moved (drafting paused). Per card: Item Finder 0.435 and CS about 0.45 still fail. P2 s2's result.json landed at 14:44, not yet read.
2. **Thesis:** rare Trainer decisions are under-credited. New after round 4 (#377): GAE's bootstrap bias at prompt rows hides an answer's effect. Queued: P6 (Monte Carlo credit, λ = 1 at prompt rows only; banded record 14:25, R-bias / R-other, 2 seeds × 30 minutes) and P4 (paired re-deal ridge value). O_B is built (split-half R 0.775 on the named five, a usable bench oracle). The per-Trainer pick counter is on from P1 block 2.
3. **Antithesis:** the answers' effect is just small. A90's power arithmetic and C99's ceiling (CS about 0.50 even with the oracle) say the per-card goal may be unreachable for CS by any credit fix, P6 included. Round 4's own measurement fits this: vine carries about 3.5x less information per rollout than PPO's GAE on the bench, so more credit methods may not beat noise.
4. **Evidence.** For the antithesis: C99 ST "between", P2 s1 null, arm 0 null on prices. For the thesis: O_B R 0.775 shows the answer values are real and stable. That makes them a learnable target, not noise. Item Finder's ceiling (C99 Amendment 3) is queued and waiting correctly behind P2 s2 (launch.log "waiting", 14:16); row 73 holds.
5. **Synthesis.** The IF ceiling is next on the GPU and decides whether IF's goal is reachable at all. Then P6 at 2 seeds reads R-bias against R-other. Both are queued and banded.
- **Checks:** bands first: P6 yes, C99 Amendment 3 yes. No stop rule breached. On focus. **Usage: 5h 55% (above round 4's skip line of 60% soon; under the cap of 75%). Week 17% against a line of about 3%: over, so fan-outs stay held (rule 18, research has adopted it).**
No RESEARCH CALL: the discriminators (the IF ceiling, P6) are queued and banded, and the next round would push the 5h window over its skip line.

A93 · 2026-10-27 15:14 · bench
1. **Ground truth.** Not moved (drafting paused). Per card: CS 0.446 and Item Finder 0.445 (P2 s2, 256 games) still fail. The draw Trainers price at or above an Energy (Professor Oak 0.56-0.64). The failures are exactly the two discard-2 cards.
2. **Thesis (shifted):** the pilot already learns the fetch, but the 2-card discard cost isn't recouped. **Amendment 7 reads "learned" (#378, #379): arm 0's greedy CS answers beat the start's on O_B (ΔG_B +0.022 ± 0.0065 and +0.011 ± 0.0050, both seeds past 2 SE, banded), while CS's price stays flat.** Running: C102 (banded at 14:48), which splits the oracle's lift into fetch and discard and logs what gets discarded. It replaced the IF-ceiling arm.
3. **Antithesis:** the discard cost is real game value, not a pilot error. The pilot's decks or game plan never get enough from one fetched card to pay for two discards, so even a perfect discard leaves both cards at or below an Energy. Then the per-card goal for these two cards is a property of the pilot's game plan (tempo, early KOs), and fetch, discard or credit fixes can't reach it.
4. **Evidence.** For the thesis's new form: learned answers with a flat price is the first effect on the bench (2 seeds, banded) that separates "can't choose" from "choice doesn't pay". It favours the discard or game-plan reading over representation or credit. P2: R-dead, null, closed (#381, #384). P1 block 1 failed its policy-fidelity gates (TV 0.110 against 0.03); a pre-registered retry runs. For the antithesis: C99 ST about 0.50 with perfect fetch+discard choices.
5. **Synthesis.** C102 discriminates: if the oracle's discard choice carries the lift and lifts both cards past 0.5, the pilot's discard is fixable. If the oracle's discard adds little, the cost is the game plan. Queued and banded.
- **Checks:** bands first: C102 yes. C99-IF was cancelled and replaced by C102 (logged, with a reason), which is fine. On focus. **Usage: 5h 67%, close to the 75% cap, and round 5 was rightly skipped (#382). Week 19% against a line of about 3%: over, so fan-outs stay held.**
- Note: the architecture arms (P2 null, R-dead; P1 failing fidelity) look less relevant now. The learned-answers result says the pilot can choose already.
No RESEARCH CALL: an effect landed in the last 2 hours (Amendment 7), and the discriminator (C102) is queued.

A94 · 2026-10-27 15:44 · Ground truth: not moved (drafting paused). Per card: CS 0.446, IF 0.445 still fail. No new progress-log entry since #384. The last bench write was 15:26 (P1 retry T0b eval at 15:21); C102 has only its record (14:48), not started. **Flag: GPU idle about 18 minutes.** Not yet a 30-minute stall. Likely the usage hold: **5h at 73%, at the 75% cap**, resets about 17:10. Week 20% against a line of about 3%: over. Thesis and antithesis as A93 (discard cost: pilot error against game plan); C102 still the discriminator, queued. No RESEARCH CALL: Amendment 7 landed within 2 hours, and a round now would break the 5h cap.

A95 · 2026-10-27 16:14 · bench
1. **Ground truth.** Not moved (drafting paused). Per card: CS 0.446, IF 0.445 still fail.
2. **Thesis being run:** P1b (P1's block 2 as a new arm, record 15:58, launched about 16:13), content-keyed cross-attention.
3. **Antithesis:** A93's. Amendment 7 shows the pilot already learns the CS answers and the price stays flat, so the bottleneck is the discard cost or game plan (C102's question), not the representation P1b changes.
4. **Evidence.** **P1 failed its recorded fidelity gate on C94's rows twice (TV 0.110, then 0.082 against a bar of 0.03; agreement 0.902 against 0.95).** By its own Amendment 4, P1 stops at block 1 (#385).
- **FLAG, null rule (bands moved after the fact):** P1b re-registers P1's block 2 with its gate moved to the bench's own rows, where T0b's values (TV 0.0275, agreement 0.973) were already known when the record was written (#386: "whose values are already known"). A gate chosen after seeing that it passes is not a pre-written band. Whatever P1b shows, its block-1 pass can't count. Its outcome bands (prices, ΔG_B) can still count if they were written before its training.
- **FLAG, priority:** C102 (A93's discriminator, banded at 14:48) still hasn't run. P1b took the GPU first, though the newest effect (Amendment 7) predicts P1b's outcome will be null. That is drift from the discriminating question toward the architecture line.
- **FLAG, usage: 5h at 79%, over the 75% cap** (resets about 17:10). The 16:09 round was rightly skipped (#388). Week 20% against a line of about 3.3%: over.
5. **Synthesis.** Run C102 before P1b's seed 2. It is evaluation only, short, and decides whether any pilot change (P1b included) can lift these two cards. Queued but not running.
No RESEARCH CALL (5h over cap); the flags go to 333-10 instead.

Note after A95 (16:15, from 333-10; auditor agrees): (1) P1b's bench-rows gate only certifies the warm start's fidelity and counts for nothing. Only P1's pre-training outcome bands can make P1b a result. (2) C102 needs new code, which waits for the usage reset (about 17:10-17:20). P1b uses a GPU that would otherwise sit idle until about 17:05, and C102 is first at the reset. P1b seed 2 is dropped if seed 1 reads null on the outcome bands, which is consistent with "no seed 2 when nothing moved". (3) No builders until the reset. The priority flag is resolved; check at A97 that C102 is running.

A96 · 2026-10-27 16:45 · Ground truth: not moved (drafting paused). Per card at the last formal read: CS 0.446, IF 0.445 fail. P1b s1 ended 16:28 and was evaluated by 16:34. Its bench_eval shows CS 0.49 / 0.48 and IF 0.41 / 0.46 (64-game cells, my raw read, not banded). Not read in the log. **FLAG, rule #389: P1b s2 launched at 16:43 with no logged reading of s1 against P1's outcome bands.** The rule says s2 gives way to C102 if s1 is null, so the read should come first. If s1 is null, s2 should stop at the reset for C102. **FLAG, usage: 5h at 87%, over the 75% cap** (resets about 17:10). Week 21% against a line of about 3.5%: over. Thesis and antithesis as A93/A95; C102 is still the discriminator, first at the reset. No RESEARCH CALL (5h over cap).

Note after A96 (16:45, from 333-10; auditor accepts): research has been asked for P1b s1's formal banded read. If s1 is null, s2 stops when C102 is ready at the reset (about 17:10-17:20). Until then s2 only fills a GPU that nothing else can use under the cap. Check at the next audit: s1's read is logged, and C102 is running by about 17:20.

A97 · 2026-10-27 17:14 · bench (long-view check)
1. **Ground truth.** Not moved (drafting paused). Per card: CS 0.446, IF 0.445 fail. **New: P1b s1 null to worse (#390-#392): CS -0.028, IF -0.008 against arm 0; head-to-head 0.468; its CS answers are worse than arm 0's (ΔG_B -0.0245 ± 0.0065).** The binding mechanism is live (count-shuffle TV +0.147). Seed 2 segfaulted, so P1b closes at 1 seed.
2. **Thesis (architecture line):** content-keyed cross-attention lets the pilot value cards. Queued: P1c, P1b at matched iterations (21+ a seed, 2 seeds, chained stages, after C102; segfault fix first).
3. **Antithesis (long view):** the bench's architecture arms are now P2 null (R-dead), P1 failed fidelity, P1b null/worse with a live mechanism. Meanwhile the plain pilot learns CS's answers (Amendment 7) and its price stays flat. Occam: the representation isn't the bottleneck. P1c's rationale ("matched iterations") is an explanation written after P1b's null. Its bands are pre-written, so it is fair to run, but its prior should be null.
4. **Evidence.** For the antithesis: three architecture arms, 0 effects. A working mechanism gave worse answers, not better. Amendment 7 (the plain pilot learns). For the thesis: only the live mechanism (binding moves the policy).
5. **Synthesis.** C102 (fetch against discard split; evaluation only) is still the discriminator, and it was due first at the 17:10 reset. **Check: C102 has only its record (14:48), not running at 17:14.** If it isn't running by the next audit, that is a stall of the agreed order. P1c should wait on C102's reading: if the discard cost is the game plan's, no architecture arm can reach the per-card goal.
- **Checks:** bands first: P1c yes. Stop rules: none breached (the s2 segfault is an error, not a breach). Usage: 5h reset at 17:10 (not in the file yet). **Week 22% against a line of about 4.5% (92% × 8.3 h / 168 h): over, so fan-outs stay held.**
RESEARCH CALL (2-hour rule: no per-card price has moved beyond its band since Amendment 7, about 14:50): does the discard cost belong to the pilot or to its game plan? Run C102 now, ahead of P1c and the segfault hunt. Research: one researcher at most (rule 18).

Note after A97 (17:16, from research #394, CPU only, no researcher): there is no game-phase pattern. The pilot's own dV across a Computer Search play is negative in every third (arm 0 -0.02 to -0.07, start -0.13 to -0.18). Discards are mostly Trainers it prices low (PlusPower, Scoop Up, Lass), and often another CS or Item Finder. Energy is only 13-27%. Auditor's reading: this is a self-consistent loop. The pilot undervalues search and recovery cards, so it discards them to CS, which makes CS look worse still. That favours "pilot valuation" over "game plan", but it is a 1-seed descriptive read, not banded. C102's S_discard arm (do oracle discards shift toward Energy, with a price lift?) is the banded test. P1c's prior is recorded as "catches up" (null on outcome).

A98 · 2026-10-27 17:44 · bench
1. **Ground truth.** Not moved (drafting paused). Per card: CS 0.446, IF 0.445 fail. **New: C102 (#396, #397, banded): oracle discards add nothing for either card or pilot (S_discard - G about 0), so R-discard fails.** That withdraws #394's lean and my A97 note's "pilot valuation" reading. The start pilot's CS lift is fetch-side (+0.067 ± 0.031), and arm 0 has learned most of it (+0.016 left). **Item Finder gains nothing from any oracle answer.**
2. **Thesis (the team's, still running):** a better representation lets the pilot value these cards. P1c is relaunched at 17:43 (P1b at matched iterations, 2 seeds).
3. **Antithesis, now the simplest reading:** with the fetch already learned, discards irrelevant and timing irrelevant (C99), both cards are at or below an Energy because that is what they are worth on this pilot's game plan. No choice the oracle can make lifts them. The open question is the game plan itself: do these decks win more with more Energy? Queued as C103 (record 17:37: win share against each P list as its Energy count moves).
4. **Evidence.** For the antithesis: C99 timing about 0; C102 discard about 0; fetch learned (Amendment 7, C102); prices flat. Four banded readings, mostly 2 seeds. For the thesis: none since P1b's live-but-worse mechanism.
5. **Synthesis.** C103 discriminates directly (does the bench pilot's game reward Energy over these Trainers at every count?). It is queued behind P1c. **It should run first:** C102 removed every choice-side route P1c could improve, so P1c's outcome prior is null.
- **FLAG, stop rule changed after it fired:** P1c s1 was killed at 17:40 by its KL rule (over 0.05 for 2 iterations). Amendments 1-2 then excluded iteration 0 and raised the bar to 0.08 (#399-#402). Excluding iteration 0 is a defensible fix for a cold-optimizer artifact, documented with arm 0's range. **The raise from 0.05 to 0.08 loosens a stop rule after it stopped a run.** Its outcome bands are unchanged, so P1c's outcome can still count, but this is the second rule moved for the P1 line today (A95: P1b's gate).
- Usage: 5h 2% (reset 17:10) / week 22% against a line of about 4.8%: over, so fan-outs stay held.
RESEARCH CALL: is the game plan the bottleneck? Run C103 before P1c's remaining stages. No per-card price has moved beyond its band since about 14:50.

Note after A98 (17:45, from research): research recommends to 333-10 that P1c pause at its next iteration boundary, C103 run (about 30 minutes, evaluation only), and P1c resume from its checkpoint. C103 bands (written beforehand): R-energy-hungry if the +4 Energy variant takes at least 0.53 with its CI above 0.5; R-flat if every ±4 point is within 0.03 of 0.5. Auditor's note on the bands: an outcome between the two (e.g. +4 at 0.51-0.53) reads as "between". R-energy-hungry would mean the pilot's game plan, not its choices, rewards Energy, which is the root of the original minimum.

Note after A98 (17:45, from 333-10; all three flags resolved): (1) C103 runs before P1c's remaining stages, and P1c pauses at its next checkpoint. (2) P1c's KL kill reverts to the pre-registered 0.05, excluding only iteration 0, and a seed already over that line counts as killed. The post-hoc loosening is withdrawn. (3) Research rounds now run only on a RESEARCH CALL, or at most every 2 hours, for the week's pace. Standing instruction: keep flagging any rule moved after it fires. Next audit checks: C103 running, and P1c paused at a checkpoint.

A99 · 2026-10-27 18:14 · bench (new result)
1. **Ground truth.** Not moved (drafting paused). Per card: CS 0.446, IF 0.445 fail. **New: C103 (#405, #406, banded, 2 seeds): neither pilot is Energy-hungry.** Under arm 0 every Energy shift from the lists' count loses or ties (-4: 0.446, +4: 0.484, +6: 0.492). Under the start pilot (C49-sd, human-free), +4 Energy is 0.509 [0.488, 0.531]: flat, a slight lean at most. The prior (R-energy-hungry) is refuted.
2. **Thesis (the team's):** the deficit is specific to Computer Search and Item Finder. Next: C105 (one extra copy of CS's top target, priced against the list; queued behind P1c) and C104 (arm 0 continued in 30-minute stages, Kill line written at 18:06, waits on C105's gate).
3. **Antithesis.** (i) Confound: arm 0 was trained on these very lists, so "agrees with the lists' Energy count" may be home advantage, a pilot fitted to those decks' curve, not evidence that the count is right. The start pilot, which was never trained on them, is the clean read, and it shows a slight +Energy lean, not hunger. (ii) Long view: the drafting minimum (+5 Energy, -4 Trainers in the best 12) may be exactly the CS/IF slots turned into Energy, since those are the only Trainers priced under an Energy. Then the whole original minimum reduces to two cards' value, which is a much smaller problem than the one the project started with.
4. **Evidence.** For (ii): C97 (only CS clearly carries the lists' deficit at the group level), the bench per-card prices, C103's flat start. Not yet checked: the drafted best-12's Trainer composition (do they drop CS/IF specifically?).
5. **Synthesis: the cheapest check costs nothing.** Read C91's and C93's best-12 decklists (files exist) and count CS, IF and the other Trainers against the lists. If the missing about 4 Trainers are mostly CS/IF, the drafting gap is the bench's two cards, and the bench's per-card goal is the right target. Not queued.
- **Checks:** P1c s2 killed by the pre-registered 0.05 rule at iterations 3-4 and recorded as its result, with no rerun (#409, #410). That is the null rule honoured. C104's Kill line was written before launch. Usage 5h 7% / week 23% against a line of about 5.3%: over, so fan-outs stay held.
RESEARCH CALL: zero-GPU check: which Trainers do C91's and C93's best 12 drop relative to the lists? Is the drafting minimum just CS/IF?

Note after A99 (18:16, auditor, on #411): **my A99 hypothesis (ii) is refuted.** The drafting gap is not CS/IF. C91's best 12 carry 27.2 Trainers against the lists' 27.5, with CS matched (+0.04). The gap is PlusPower -2.71, Gust -2.42, Item Finder -1.96, Scoop Up -1.71, Sneak Attack -1.38, SER -1.21, traded for Gambler +2.96 and the Energy Trainers (+1.5 to +1.9). Fresh gated screens also lack CS -2.1 and Oak -2.0. **Flag, focus:** PlusPower is the bench's lowest price under arm 0 (0.432), so it fails the per-card goal (row 98) too. Yet the bench's work and lists of failing cards name only CS and IF. The ground-truth gap points at tempo and attack-support Trainers (PlusPower, Gust), which the CS-centred queue (C105, P1c) doesn't test. Next audit: check that the per-card readouts list every failing Trainer, and whether a PlusPower/Gust probe is queued.

NOTE, BENCH FOCUS CARDS (333-10, about 18:30, from #411; read at every audit until replaced): the focus cards are PlusPower, Gust of Wind, Item Finder and Scoop Up, with Computer Search as reference. PlusPower and Gust are priced at 256 games in every arm, and arm 0 is re-priced for them as the baseline. C105 (15 minutes, the CS reference) stays. After it, the next probes target PlusPower and Gust. If C104 runs, it prices all four focus cards per stage. Audits read per-card prices on this list (row 98: each at least 0.5 within its noise).

A100 · 2026-10-27 19:41 · bench (new results, long view)
1. **Ground truth.** Not moved (drafting paused). **Focus cards at 256 games (#417, #418): PlusPower, Gust, Item Finder, Scoop Up and CS all price 0.43-0.47 pooled under the start and both arm 0 seeds. None meets the per-card goal.** The game-count check found no bias (#425, #426).
2. **Thesis:** PlusPower's policy runs backwards. **C108 (#427, #428): every pilot plays PlusPower 4-6x more often when no attack is legal (start 0.132 against 0.022 with an attack), although the encoder separates the two states (probe AUC 0.93).** So it is a credit or sequencing failure, not representation. Running: BENCH-P5 (launched 19:11), training-time branching at PlusPower decisions scored by the pilot's own value (row 83; no oracle copying).
3. **Antithesis (long view, every oracle ceiling so far):** C99 CS ST 0.50-0.54; C102 discards about 0; C105 CS's best fetch capped at about an Energy (0.482); **C106 perfect PlusPower timing +0.05, to 0.51-0.52, while missed knockouts fall from 0.63 to 0.03 a game; C107 Gust oracle +0.013 / +0.022.** Fixing the decision rarely moves a card past an Energy. Even a converted knockout barely changes the result in this pilot family's games. The rival: tempo cards pay off only when games are decided by tempo, i.e. against strong opponents. Between two weak pilots a consistent Energy is worth as much. Then the bench's ≥0.5 goal depends on opponent strength, not on the pilot's handling of the card.
4. **Evidence.** For the thesis: C108's backwards policy is real and cleanly measured, and P5 can fix it. For the antithesis: four oracle ceilings at about 0.5, and knockouts converted without a matching price gain.
5. **Synthesis: the cheapest discriminator.** Price PlusPower (with the C106 oracle timing) against opponents of rising strength: the start, arm 0, and an oracle-timed opponent. If PlusPower's value rises with opponent strength, the goal needs stronger self-play opponents (a league), not card fixes. If it stays flat, the card is worth about an Energy for this engine and pilot family. Not queued. P5's record was written at 19:01, before its 19:11 launch, with bands (2 seeds) and the 0.05 KL kill: bands first, OK.
RESEARCH CALL: does a tempo card's value depend on opponent strength? Run a PlusPower price across opponent strength (start / arm 0 / oracle-timed), before more card-specific fixes. Usage 5h 22% / week 25% against a line of about 5.7%: over, one researcher at most.

Note after A100 (19:42, from research #430; no researcher spent): C109 is recorded with bands first. The PlusPower side is held fixed (arm 0 + oracle timing, lists 3/1/21), and only the opponent (the Energy-copy side) gets stronger: start → arm 0 → arm 0 + S oracle, with a strength check, 2 seeds. R-rising if +0.03 from O1 to O3 at both seeds (the goal needs stronger opponents, a league); R-flat if within 0.03 (about an Energy is its bench value). Prior: flat. Runs after P5 (no GPU beside an arm). Auditor: the design is sound. If R-flat, the per-card goal (row 98) looks unreachable for tempo cards in this family, and that should go to Evan.

A101 · 2026-10-27 20:41 · bench
1. **Ground truth.** Not moved (drafting paused). All focus cards are still 0.43-0.47 at 256 games.
2. **Thesis:** PlusPower's backwards policy is a credit failure. **P5 (#432, #433, banded, 2 seeds): R-not-learned by its letter. The sign didn't flip, but the gap shrank from -0.028 / -0.017 to -0.015 / -0.004, and attack-present plays rose 5-7x. Missed knockouts are unchanged.** A partial move on mechanism, null on outcome. Next: C110 (CPU, KO math).
3. **Antithesis:** A100's (tempo value depends on opponent strength). **It is still untested: C109 was confounded by design (#435, research's own admission).** Only the Energy-copy side's pilot got stronger, so it measured the pilot gap, not the card's value. The +0.24 / +0.26 rise is pilot strength. It reads "between", no claim. The one clean equal-strength cell puts oracle-timed PlusPower about even with an Energy.
4. **Evidence.** For the thesis: P5's mechanism moved but outcomes didn't, which fits "even a correctly timed PlusPower is worth about an Energy here" (C106). For the antithesis: no valid test yet.
5. **Synthesis: the corrected C109.** Both decks piloted by the same pilot at each of three strength levels (start / arm 0 / arm 0 + S oracle on both sides), PlusPower oracle-timed, 2 seeds, bands first. If the PlusPower copy's share rises with joint strength, a league is the route. Not queued.
- **Checks:** a design confound was caught and recorded as no claim, not spun. The null rule held. No rule moved. Usage 5h 23% / week 25% against a line of about 6.4%: over; the 19:46 research slot was rightly skipped.
RESEARCH CALL: rerun C109 with equal-strength pilots on both sides at three strength levels; it is A100's question, still untested.

Note after A101 (20:43, from research #436): C111 (runs/probe/C111-symmetric-strength/) is A101's design. The same pilot sits on both sides at start / arm 0 / arm 0 + S, with T on the list side, 256 games a pair, 2 seeds; implementation has been asked to run it now. Bands on pooled Δ = L3 - L1 (SE about 0.018): R-rising at Δ of +0.04 or more and positive at both seeds; R-falling mirrored; R-flat at |Δ| < 0.04. Prior: flat. Auditor: a gap remains (|Δ| at or above 0.04 with the seeds disagreeing); read that as "between". C109b is withdrawn. This is the test that bears on the ground truth, because drafting prices cards with the same pilot on both sides.

A102 · 2026-10-27 21:41 · bench (new results, long view)
1. **Ground truth.** Not moved (drafting paused). Focus cards under the pilots' own play are still 0.43-0.47. **New: C111 R-flat (#444, #446, banded, 2 seeds): oracle-timed PlusPower is worth about an Energy or slightly more at every symmetric strength (start 0.526, arm 0 0.519, arm 0 + S 0.533; Δ +0.007 ± 0.018).** By the default reading it meets the per-card goal in every list.
2. **Thesis (now the best-supported):** PlusPower's deficit is timing, a credit failure. The input is there: **C110b (#442, #443), the PlusPower option's scoring input separates conversion from no-KO states at AUC 0.915-0.926, and the opposing Active token holds HP left at R² 0.99.** Running: P5b (P5 continued 30 minutes; s1 killed by KL, s2 running), then P5b-w (a cold-start warm-up rerun).
3. **Antithesis.** A100's opponent-strength rival is **refuted** by C111. The remaining rival: P5's branching signal is real (it favours PlusPower in conversion states, +0.07-0.09), but PPO's update can't apply it within the KL budget. Every cold-start arm trips KL, so the step size, not the signal, is the binding limit. Then more branching won't help; a larger trust region or a separate advantage head would.
4. **Evidence.** For the thesis: C110b (the info is at the policy's input), C111 (correct timing is enough), P5's partial move (the gap shrank by about half). For the rival: 4 of 4 cold-start arms killed by KL (#447); P5b s1 killed while its signal stayed correct.
5. **Synthesis.** P5b-w with Adam warm-up (Amendment 3) separates "cold-optimizer artifact" from "the step-size limit binds". If warm-up runs clear the KL rule and the sign flips, it was the optimizer; if they still trip it, it is the step size. Queued.
- **Checks:** Amendment 3 is a forward-only protocol change. s1 stays killed as its result, and the rerun is a separate arm (P5b-w). It is not a loosened kill: the 0.05 rule is unchanged. OK, but it is the third KL-related amendment today; keep the kill fixed. Usage 5h 30% / week 26% against a line of about 6.9%: over.
- **Long view:** the bench has now localised one card fully (PlusPower: info present, the timing is the fix, worth about an Energy+ when timed). That is the first concrete route back to the ground truth: if P5-style credit fixes PlusPower's timing, a re-drafted pool should keep PlusPower.
No RESEARCH CALL: a banded result landed (C111), and the discriminator (P5b-w) is queued.

A103 · 2026-10-27 22:41 · bench (P5 line closed)
1. **Ground truth.** Not moved (drafting paused). Focus cards under the pilots' own play: 0.43-0.47. **The P5 line stopped by its pre-decided gate (#456-#458): P5b-w s1's checkpoint prices PlusPower at 0.455 ± 0.013 pooled (bar 0.472, or 0.50 in 2 of 3 lists; arm 0 0.442).** Missed conversions fell (0.64 → 0.26) only by playing PlusPower about 4x more in every state (R3 about 0). The gate held; P5c was not launched.
2. **Thesis (new): myopia.** The one-turn comparator can't see a held PlusPower's value (holding it for a later knockout), so branching teaches "play it with attacks", not "hold it". C112 (a next-turn horizon check) is written but not run; it needs a build of about 50-70 lines.
3. **Antithesis:** the oracle in C106/C111 is also one-turn (T), yet it lifts PlusPower to about 0.52. So a one-turn signal *can* express the right timing, and the failure is in learning from it (step size / KL: P5b-w was killed at iterations 14-15), not in the horizon.
4. **Evidence.** For myopia: R3 about 0 (no state-selectivity learned); research round "Holding value" says all-action methods inherit a zero advantage. For the antithesis: the one-turn oracle's +0.05; P5's signal favoured PlusPower in conversion states (+0.08-0.11), which a one-turn comparator can't produce if it were blind. Research's own correction (#461): the preview was underpowered (+0.013 measured against a predicted +0.02-0.03, SE about 0.02). The stop stands as pre-registered, and the wording was softened, not the gate. OK.
5. **Synthesis.** C112 (hold against play scored at this turn's end and at the next turn's end, no training) discriminates directly. If next-turn scoring shows holding beats playing in no-KO states while this-turn scoring doesn't, it's myopia. Written, not queued (it needs the horizon build).
- **FLAG, usage misread:** #461 records the 22:34 round as run at "week 3%". ~/.claude/usage-latest.json reads **week 28%** (22:41) against a line of about 7.9%. The round (1 researcher + writer) was within rule 18's size, but it ran on a wrong reading. P7 is written and held for this audit. The round recommends against it, and so do I: its advantage is zero by construction.
- Also note: P5b-w's 0.80 first-step KL came from the zero-LR warm-up itself (#453, implementation's error, recorded).
RESEARCH CALL: build C112's horizon flag (about 60 lines, CPU-first) and run it before any P7 or P5c. It decides myopia against step size. Usage: 5h reset (not in file) / week 28%: over.

Note after A103 (22:43, auditor, on research #464): (1) I withdraw the usage "misread" flag. Research quoted the file raw: 3% at 22:34 and 5% at 22:42. I read 28% at 22:41, so the file flips between writers minutes apart, probably several sessions or accounts. Rule adopted: take the higher reading. Rounds back to every 2 hours at minimum breadth. (2) C112 is answered from logs, no build (#462-#464). The one-turn oracle T attaches PlusPower before most attacks (r 0.955 / 0.774) and doesn't hold. It catches about 0.17 conversions a game against the learned pilots' 0.003-0.09. So A103's antithesis holds: horizon isn't the gap, the update size is. **FLAG, a rule moved after it fired:** #456 (written before the preview was read) said P5c runs only if the checkpoint price pools at 0.472 or more (or 0.50 in 2 of 3 lists), "otherwise the P5 line stops". #457 read 0.455, so it stopped. P5c is now launching "on the pre-decided go" after #461 re-read the preview as underpowered. That reverses a pre-registered stop on a post-hoc power argument. If P5c runs, its result can count only against its own new bands, and the #456 stop should be recorded as overridden, by whom and why.

Note (22:44, auditor): the P5c override is logged as its own entry (who: 333-10 under row 100; why: #461 found the gate underpowered and the no-GPU check read "catching"). P5 stays stopped at #457/#458. P5c counts only against its own bands (conversions at least 0.12 a game; PlusPower at least 0.472 pooled at 256). The flag is resolved. Usage: 333-10 reports week 5-6%, but this session read 28% at 22:41. Under the take-the-higher rule the week stays treated as over its line until the file's writers are reconciled.

A104 · 2026-10-27 23:41 · Ground truth: not moved (drafting paused). P5c (a new experiment under the #465 override; bands set before launch; the Adam first-moment reset removed the first-step KL overshoot, 0.015 against 0.80) has s1 trained and evaluated (23:26), not yet read in the log; s2 running since 23:39. (bench_eval has no PlusPower key the auditor could read, so there is no raw number here.) Not stalled, on focus, no rule moved since #465. Usage: 5h 46% / week 6% in this reading (line about 8.4%, under; the 28% reading at 22:41 is unresolved, so per the take-the-higher rule fan-outs stay lean). No RESEARCH CALL: P5c is the queued discriminator (step size), mid-flight.

A105 · 2026-10-28 00:41 · bench (new result, long view)
1. **Ground truth.** Not moved (drafting paused). **P5c reads "between" (#468-#470, banded, 2 seeds):** knockouts caught 0.053 / 0.089 a game against the 0.12 bar (T 0.16-0.17); PlusPower pooled 0.463 / 0.47201 against the 0.472 bar. s2 sits on the line (725/1536), so this is no claim either way. The price tracks conversions caught (+0.02-0.03 over arm 0, about 1-1.4 SE). Per card, every focus card still fails.
2. **Thesis:** the credit signal is right, but PPO's KL-bounded steps move the policy too slowly. **P5c measured it: kl-stop cut 58-65% of minibatches.** Running: P8 (P5-gen, launched 00:33): play-or-greedy branches at every Trainer-playable decision, no card list, about 10 branched rows a game, banded on the four focus cards' mean price against arm 0.
3. **Antithesis to P8's step:** if KL pace is the binding limit (P5c's own finding), spreading the same KL budget over all Trainers gives each card less movement than P5c gave PlusPower, which didn't reach the bar. P8 generalises before the specific case has worked. Occam: the dial P5c points at is training time under the same KL, not breadth.
4. **Evidence.** For the thesis: catches and price rise together (consistent, under 1.5 SE), and KL bound most updates. For the antithesis: P5c "between" at 30 minutes; the earlier P arms also all ran at 30 minutes. No arm has been run longer.
5. **Synthesis.** P5c continued in chained 30-minute stages (same bands, the 0.05 KL kill unchanged, stop after each stage if catches don't rise) against arm 0 continued for the same time (C104 exists as the matched base). If catches pass 0.12 and the price clears 0.472 with time, pace was the limit, and P8 should follow, not lead. Not queued; P8 took the slot.
- **Checks:** P8's record file was last modified at 00:34, a minute after its 00:33:14 launch. Bands-first is to be confirmed: see the note below. P5c's knife-edge tie was resolved by the raw counts and recorded as "between": honest, no claim. No rule moved. Usage 5h 49% / week 6% (line about 9.2%, under in this reading; the 28% reading is still unresolved).
RESEARCH CALL: is training time the dial? Run P5c-long against C104 (matched arm-0 continuation) in chained stages before reading P8 as a generalisation. No per-card price has moved beyond its band in 2 hours.
- Note to A105 (P8 bands): the record header says "written before launch". The 00:34 change is a dated smoke note plus a prediction "written before any training readout", appended at launch. The bands themselves predate launch, so OK.

A106 · 2026-10-28 01:41 · bench
1. **Ground truth.** Not moved (drafting paused); focus cards still fail per card. **New: P8 (Trainer-wide branching) gives no lift and some harm (#475, #476, banded).** s1 was killed by the KL backstop (iterations 15-16). s2 reads R-not: focus-card mean 0.448 against arm 0's 0.461, no card up, head-to-head 0.421 ± 0.015, past the harm line. This matches its own pre-readout note and A105's antithesis: the same KL budget spread thinner. 0 effects / 1 null (harmful).
2. **Thesis:** pace, not breadth, is the dial. Running: P5d (P5c's seeds continued in up to 3 warm 30-minute stages; stop if catches don't rise +0.01 a stage; bands on catches of at least 0.12 and on the price; C104 the matched base). Launched (arm-p5d-s1 writing at 01:41).
3. **Antithesis:** a slow but steady pace can't close the gap either. If catches rise but the price stays under 0.472 at matched time with C104, PlusPower's price is limited by something besides timing, e.g. the pilot's attacks aren't strong enough for +10 to matter often. C106's oracle gain of only +0.05 already says the ceiling is low.
4. **Evidence.** For the thesis: P5c's catches and price moved together, and P8's harm came from a thinner budget. For the antithesis: the oracle ceiling of +0.05 (C106/C111: 0.52-0.53). So even a perfect P5d reaches only about 0.52. The per-card goal is then met by the default reading, and only just.
5. **Synthesis.** P5d is the discriminator and is running. No other test is needed now.
- **Checks:** P5d's bands and stop rule were written before launch (#473). P8 was read against its pre-readout prediction, honestly. No rule moved. **Usage: the file again shows two writers in one window** (00:41: 5h 49%, week 6%; 01:41: 5h 7%, week 29%; same 5h reset time). Taking the higher readings: **week 29% against a line of about 9.7%: over.** Fan-outs held, rounds lean.
No RESEARCH CALL: P5d, the discriminator, is mid-flight.

A107 · 2026-10-28 02:41 · bench (new result, long view)
1. **Ground truth.** Not moved (drafting paused since about 10:30, 16 hours). **New: P5d stopped after stage 1 by its rule (#478):** knockouts caught a game 0.0697 against P5c's 0.071 (it needed +0.01). The attach pattern is still inverted. PlusPower 0.465 / 0.485, and s1 is under 0.472. **Training time is not the dial either.**
2. **Thesis (exhausted on PlusPower):** timing credit. Every route on it now reads null or between: P5 stopped; P5c between; P5d flat; P8 harmful.
3. **Antithesis (long view of the bench):** 16 hours of bench work have produced **0 per-card effects.** The one effect (Amendment 7: CS answers learned) left its price flat. Every oracle ceiling sits at about an Energy (CS 0.50-0.54, PlusPower 0.52-0.53, Gust +0.02, discards about 0, fetch capped 0.48). The simplest reading: in this engine, under this pilot family, a marginal Trainer copy is worth about a basic Energy, so the per-card goal (row 98) is at the edge of what's reachable even with perfect play. Meanwhile the ground-truth gap is small and known (C91: Trainers 27.2 against 27.5; the gaps are tempo cards ±2-3 copies; G3 0.57 with the A82 caveat).
4. **Evidence.** Bench: 0 effects; nulls P2, P1, P1b, P8 (harmful), P5 (stopped), P5d (stopped); betweens C99, C111-flat, P5c. Ground truth: C93's gate is the only effect on G1 (4 seeds).
5. **Synthesis: this is Evan's decision, not an experiment.** Two options. (a) Keep the bench and change its goal: say what per-card target is meaningful when oracle ceilings are about 0.52. (b) Return to drafting with the gate as base (A76) and read G1 and the tempo-card counts directly. The bench's lessons go along: the oracle ceilings, the inverted PlusPower policy, and the fact that KL pace binds.
RESEARCH CALL: no new probe. Write a one-page summary of the bench's findings for Evan, with options (a)/(b) and a recommendation, via 333-10. No metric has moved in 2 hours, and every queued bench line has closed. Usage 5h 9% / week 29% against a line of about 10%: over, so no fan-out.

A108 · 2026-10-28 03:41 · Ground truth: not moved (drafting paused). P5 line ended (#479: R-plateau, the comparator teaches about 40% of the oracle's catching, then stops). The bench summary for Evan is written (#480), recommending (b): resume drafting from the gate base and read G1 plus the tempo-card counts. **Waiting on Evan's decision. The idle GPU is a decision wait, not a stall.** No new runs. Usage: 5h reset (not in file) / week 30% against a line of about 10.6%: over. The A107 research call was answered (#480), so no new call.

A109 · 2026-10-28 04:41 · Ground truth: not moved (drafting paused). Nothing new; still waiting on Evan's (a)/(b) decision (#480). The idle GPU is a decision wait, not a stall. Usage 5h 0% / week 30% against a line of about 11.1%: over. No RESEARCH CALL: the open question is Evan's, not empirical.

A110 · 2026-10-28 05:41 · Ground truth: not moved. Nothing new; waiting on Evan's (a)/(b) decision (#480), so not a stall. Usage 5h 5% / week 31% against a line of about 11.7%: over. No RESEARCH CALL (the question is Evan's).

A111 · 2026-10-28 06:41 · Ground truth: not moved. Nothing new (only #482, a skipped research round); waiting on Evan's (a)/(b) decision (#480), so not a stall. Usage 5h 5% / week 31% against a line of about 12.1%: over. No RESEARCH CALL (the question is Evan's).

A112 · 2026-10-28 07:41 · Ground truth: not moved. Nothing new; waiting on Evan's (a)/(b) decision (#480) since about 03:00, so not a stall. Usage 5h 6% / week 31% against a line of about 12.5%: over. No RESEARCH CALL (the question is Evan's).

A113 · 2026-10-28 08:41 · Ground truth: not moved. Nothing new (#483, a skipped round); still waiting on Evan's (a)/(b) decision (#480), about 6 hours now, so not a stall. Usage: 5h reset (not in file) / week 31% against a line of about 12.9%: over. No RESEARCH CALL (the question is Evan's).

A114 · 2026-10-28 09:42 · engine audit (Evan row 102, about 08:50: "Why would the engine reward something different? It's the same game")
1. **Ground truth.** Not moved (drafting paused; Evan's direction is now the engine audit, which supersedes the (a)/(b) wait). **New, the audit (#484-#496):** the engine's suites pass (267 + 714 specs, 0 failures); card data matches a printed reference for all 225 pool Pokémon; the enumerator offers every legal action (29,936 decisions, 0 mismatches); the 2000 rules play as written (32 PASS, 0 FAIL, 3 untested); only minor card faults, off the bench. **The one structural finding: 81% of bench games hit the turn cap, and a capped game goes to the player ahead on Prizes (#486).** So the reward is mostly "Prizes ahead at turn T", with about 3.4 knockouts a game.
2. **Thesis (now Evan's question):** the game is right, but the scoring is not the real game. A turn cap with a Prize-lead tiebreak rewards early, cheap Prize trades (Energy, attackers) over setup and tempo Trainers. Running: C113 (record 09:12, launched 09:14): M and the four focus cards under (i) the current cap, (ii) untimed, (iii) the real STS time rule as scored at the event.
3. **Antithesis:** earlier untimed checks already went the other way. C59 priced the search group lower untimed (0.375 against 0.412), and C98 priced CS lower untimed (0.40 against 0.44) on 2 seeds. So removing the cap may *lower* Trainer prices, not raise them. And 81% capped may simply reflect slow pilots, not the cap's design.
4. **Evidence.** For the thesis: the 81% cap share is a real fact, so the reward is mostly the tiebreak. For the antithesis: two banded untimed readings, both lower. C113's arm 0 and start cells are written (09:16-09:40), with the readout pending.
5. **Synthesis.** C113 is the discriminator, running, banded first. Read the four focus cards under (ii) and (iii) against (i). If they rise above 0.5 untimed or under the real rule, the scoring was the fault. If they fall again (as C59/C98), the cap isn't the bottleneck, and the remaining explanation is the pilot family's game strength.
- **Checks:** C113 bands first (record 09:12, launch 09:14). On Evan's new direction. **Usage: 5h 0% / week 31% against a line of about 13.3%: over.** The audit used 2 Haiku readers + 1 Sonnet builder (196k tokens) + a deep-research round. That is under Evan's request (row 102), but rule 18 holds fan-outs while the week is ahead. Keep it to that.
No RESEARCH CALL: C113 lands within the hour.

A115 · 2026-10-28 10:41 · engine audit (new results, long view)
1. **Ground truth.** Not moved. **New: C113 reads R-rule-matters, against the lists (#497, banded).** M (each list against its copy with 6 Trainers as Energy) is 0.49-0.50 under the current cap, 0.375-0.384 untimed, and 0.389-0.398 under the real-STS stand-in. Played longer, the lists lose more to their Energy copies. A114's antithesis (untimed lowers Trainers, as C59/C98) is confirmed, and the cap was flattering the lists. **C114 (#501, #502, "between"): every pilot, SimpleBot included, needs a median 24-28 own turns to take six Prizes, against the roughly 7 cited for real play.** Training moved arm 0 toward attrition (knockouts -19%, retreats x2.7).
2. **Thesis (the team's, P9 held):** the pilots play a slow attrition game, so in long games Energy beats Trainers. Fix pace with a per-turn discount (BENCH-P9, γ 0.98 a turn, written and held).
3. **Antithesis (by working rule 9, environment first):** SimpleBot, a scripted player that never plays Energy Removal, is also at 24-28 turns. Slowness shared by a scripted bot and every learned pilot points at the environment or the decks' matchups, not at learning. The roughly 7-turn figure also needs a source. If real games run 7 own turns and the engine's run 24+ even for a bot, something in the engine's game flow (damage, Energy attachment, first-turn rules, draws) is slower than the real game. The rules audit checked rules item by item, not pace end to end.
4. **Evidence.** For the thesis: arm 0's attrition shift (a learned effect toward slowness) and C113's direction. For the antithesis: SimpleBot shares the 24-28-turn pace; the rules PASS on each item doesn't rule out a pace-level discrepancy. The "about 7 turns" figure is unsourced in my reading.
5. **Synthesis: the cheapest discriminator, CPU, minutes.** A goldfish test: each P list against a do-nothing opponent (passes every turn), scripted greedy attacker. How many own turns to take six Prizes? Hand calculation for list 3 (Haymaker: Hitmonchan/Electabuzz against 60-70 HP bench-fillers) suggests about 7-10. If the engine's goldfish is near that, the slowness is interaction, so P9 is the right fix. If the goldfish is about 20, the engine's flow is off, so audit it before any training. Not queued.
- **Checks:** C114 and C113 bands first; P9 written and held, not launched. **Usage: 5h 19% / week 33% against a line of about 13.8%: over.**
RESEARCH CALL: is the engine's game pace right? Run a goldfish test (P lists against a passing opponent, own turns to six Prizes) before P9, and source the "about 7 turns" real-play figure.

Note after A115 (10:43, from research): C115 goldfish (runs/probe/C115-goldfish/) runs before P9. Each P list attacks a passive copy that benches Basics and passes; SimpleBot first, then arm 0. Bands on SimpleBot: R-interaction at 10 own turns or fewer to six Prizes in 3 of 4 lists (P9 right); R-flow at 16 or more (audit the engine's flow first). Prior: 8-12. Auditor: 11-15 is "between", no claim. The "about 7 turns" figure is sourced (C02: two authors, Chad Mills' Wigglytuff notes and STS report, plus an October 2000 player's game, all best-case speed claims, rated medium-low). So it is a goldfish-like ceiling, not a typical game, and the goldfish test is the fair comparison.

A116 · 2026-10-28 11:41 · engine and pace (new results, long view)
1. **Ground truth.** Not moved. **New, the clearest causal chain yet:**
   - **C115 R-flow by its bands, then explained (#505-#511):** uncontested, the lists still take a median 19-32 own turns to six Prizes (SimpleBot 27-32, arm 0 19-26). But the engine's flow checks are normal: opening hands and mulligans at the hypergeometric expectation, damage as printed on 94-100% of hits, Do the Wave exact.
   - **The gap is in the pilots:** Professor Oak or Bill sits unplayed on 79-96% of the turns held, and PlusPower goes on 0-0.6% of Wigglytuff's attacks.
   - **C115b (#513, #514, "between" by its bands):** a scripted best-case Wigglytuff line reaches six Prizes in a median 9 own turns when its pieces arrive (59% of games), against the human best case of about 7 (sourced, best-case only).
   - So the engine and the decks can play near human pace, and the pilots don't. Slow games then favour Energy (C113: M 0.38-0.40 untimed).
2. **Thesis:** the pilots skip the speed Trainers, so games run 3x slow, and in slow games Energy beats Trainers, which drives the drafts' Energy lean. Next: BENCH-P9 (per-turn discount γ 0.98) to reward pace.
3. **Antithesis:** a discount rewards speed in general but doesn't fix why the pilot holds Oak and Bill. Across today, every card with a hand or discard cost is under-played or under-priced: CS and IF (discard 2), Oak (discard the hand), and Bill and PlusPower (held). The simplest single cause is a value bias toward keeping cards in hand (hand-hoarding), and P9 doesn't test it. If it is the cause, P9 may speed attacks while Oak and Bill stay held.
4. **Evidence.** For the thesis: the flow is normal; the scripted line reaches 9 turns; the pilots' 19-26. For the antithesis: #394 (the pilot's own dV across a CS play is negative in every third); the held rates for Oak and Bill (79-96%) fit a value that prices a hand card above its use. Not yet measured: the pilot's dV across an Oak play against the MC outcome.
5. **Synthesis: the cheapest discriminator, no training.** For held Oak/Bill turns, compare the pilot's own value of "play" against "hold" (dV) with a CRN branch outcome (the O_B machinery, evaluation only). If branches say play wins but dV says hold, it is a value bias, so fix the value (e.g. branch-trained V) before P9. If both say hold, play-tempo is the issue, and P9 is right. Not queued.
- **Checks:** every run bands first; C115 and C115b read honestly, against their priors. Pace sources rated medium-low and flagged unverified (403 pages). **Usage 5h 22% / week 34% against a line of about 14.3%: over.**
RESEARCH CALL: is the hold on Oak/Bill a value bias? Run the dV against branch-outcome comparison on held Oak/Bill turns (CPU and O_B, evaluation only) before P9.

Note after A116 (11:42, from research #515): C116 (runs/probe/C116-draw-hold/) runs before P9. At arm 0's held Oak/Bill turns it compares dV (the pilot's one-ply value of play against hold) with Δ_branch (CRN playouts to game end, 8 re-deals, training reward), plus a turn-end branch. Bands per card: R-value-bias / R-hold-right / R-both-play. It is split by cards left in deck (deck-out risk). Prior: bias early, hold right late, pooled between. Auditor: the deck-size split is a good control. Read the early-game cells as the main test, since late holds may be legitimately right.

A117 · 2026-10-28 12:41 · pace (new result)
1. **Ground truth.** Not moved. **New: C116 reads R-hold-right for Oak and Bill (#518, #519, banded).** At arm 0's held turns, playing Oak costs -0.049 [-0.083, -0.015] of training reward over game-end CRN branches, more so as the deck thins, and the value agrees (dV -0.177). Bill is flat. **My A116 antithesis (a hand-hoarding value bias) is refuted:** the value is right about its own game.
2. **Thesis:** the long-game loop is self-consistent. Slow play makes the draw Trainers (deck thinning, deck-out risk) and tempo cards worse, which justifies the slow play. Breaking it needs a pressure toward pace: BENCH-P9 (γ_T 0.98 a game turn) launched 11:59, 2 seeds, about 2 hours, with the γ = 1 identity check passed.
3. **Antithesis:** the loop may be held by the scoring rule, not the discount. Under an untimed or real-STS end rule (C113), Energy copies win more, so any pilot trained on long games gets pulled back. A discount changes the learner's horizon, but the evaluation reward is unchanged, so P9's price readouts may still score Trainers low. Then the lever is the training opponent's pace (a fast scripted opponent such as C115b's Wigglytuff line as a sparring partner?), not γ. Careful with row 60 there: it would be an opponent to play against, not answers to copy.
4. **Evidence.** For the thesis: C116 (self-consistent holds), C115/C115b (speed is reachable). For the antithesis: C113 (long games favour Energy at evaluation).
5. **Synthesis.** P9 is the running test of the thesis. Its readouts under all end rules (#521: points under the cap, real-STS iii-b at arm 0's fixed T) will show whether pace rises and whether Trainer prices follow. If pace rises but prices stay flat, the antithesis holds. Running; no other test is needed now.
- **Checks:** bands first for C116 and P9. C116's record was changed at 12:02, after its 11:50 summary (see the grep line above: a readout appended, not bands). **Usage 5h 29% / week 35% against a line of about 14.8%: over.**
No RESEARCH CALL: P9 is the discriminator, mid-flight.

A118 · 2026-10-28 13:41 · Ground truth: not moved. No new log entry since #521. P9 is in its readouts (eval-p9-s2 written 13:28; P9 folder 13:40), not stalled. Usage: 5h reset (not in file) / week 35% against a line of about 15.3%: over. No RESEARCH CALL: P9, the discriminator, is reading out.

A119 · 2026-10-28 14:41 · pace (new result)
1. **Ground truth.** Not moved. **New: P9 reads "between" (#522, #523, banded, 2 seeds).** The discount (γ_T 0.98) changed how mirrors end: knockouts per own turn 1.13x arm 0 at both seeds (bar 1.2), deck-outs -9 and -14 points, retreats down. But M under the real-STS clock is unchanged (+0.000 / +0.007; bar +0.03), and so are goldfish pace, Oak and Bill play, and PlusPower. The discount doesn't produce the Trainer play that makes games fast.
2. **Thesis (now):** the pilot never explores Trainer plays enough to learn their value in fast lines. Running: BENCH-P10 (13:52), forced uniform Trainer plays at ε 0.10, masked from the policy loss, outcomes credited to the value. Banded on Oak and Bill play (0.25 or more), with the ε 0 identity check passed.
3. **Antithesis (A117's, still untested):** the loop is held by the game the pilot meets, not by exploration. Against slow opponents, holding Oak is correct (C116), so exploration will confirm "hold" and the value won't change. Only a faster opponent makes the draw Trainers worth playing.
4. **Evidence.** For the antithesis: C116 (hold is right in its own games), P9 (pace pressure from the discount didn't change Trainer play), C113 (long games favour Energy). For the thesis: Oak and Bill are held on 79-96% of turns, so their play outcomes are rarely sampled.
5. **Synthesis: the cheapest discriminator, evaluation only, CPU.** Re-run C116's Oak/Bill branch comparison with the opponent replaced by C115b's scripted fast Wigglytuff line (an opponent to play against, not answers to copy). If branches then say "play Oak" early, the opponent's pace holds the loop, and P10's exploration against slow self-play won't break it. If branches still say hold, exploration is the right lever. Not queued.
- **FLAG, process:** #524 wrote P10 "held for Evan", and #525 calls the next step "Evan's decision", but #526 launched P10 at 13:52 on 333-10's call under row 100. Row 100 does allow bench arms without approval, so it is within the rules. But a decision logged as Evan's was taken without him; it should be logged as 333-10's call, not left ambiguous. Bands first: P10 yes.
- Usage: 5h 6% / week 36% against a line of about 15.8%: over.
RESEARCH CALL: does the opponent's pace hold the loop? C116 against C115b's fast scripted opponent (evaluation only), before P10 is read.

Note after A119 (14:55, from research #530): C117 (A119's test) is **invalid** by its pre-written validity check, so no band. C115b's scripted line isn't fast against an interacting pilot (0.069 knockouts per own turn, 0.71x arm 0's mirror rate), and the pilot beat it 78%. Unbanded lean: in these faster games Oak still doesn't pay (early -0.035 [-0.079, +0.008]; pooled -0.058 [-0.111, -0.006]), and Bill is flat. That leans against A117/A119's antithesis ("holding is right only because games are slow"). Recorded as a lean, not an effect. A valid test needs an opponent fast against this pilot, grown by self-play, which is a design question for Evan's bench-or-drafting call. Auditor's update: the opponent-pace antithesis is weakened; P10 (exploration) is now the live test.

A120 · 2026-10-28 15:41 · pace (new result, long view)
1. **Ground truth.** Not moved. **New: P10 closes R-not (#532, #533; s1 KL-killed, s2 alone).** The forced Trainer plays taught the value what follows a played Oak (dV -0.073, now matching the playouts' -0.069; arm 0's was -0.177). Since that is a loss, the policy played Oak and Bill *half* as often (0.078 against 0.158). M didn't move, and head-to-head was weaker (0.424).
2. **Thesis (exploration):** refuted. Exploring confirmed that Oak loses for this pilot.
3. **Antithesis, a unifying reading:** every resource-generating card loses for this pilot family: Oak (draw 7), Bill, CS and Item Finder (search), even in faster games (C117 lean). Energy, which is usable at once, wins. The simplest single cause is weak **continuation play**: the pilot can't convert the extra cards a draw or search card brings, so the resources are worth less than one Energy. That would explain the low prices (C97-C105), the slow pace (C115) and the drafts' Energy lean together. It also fits C99/C106: an oracle on *one* decision gains only about +0.05, because the turns after it are still played by the weak pilot.
4. **Evidence.** For it: P10 (playouts under the pilot's own continuation say Oak loses), C116, the C117 lean, and the uniform ceiling of about an Energy across one-decision oracles. Against it: none yet; it hasn't been tested directly.
5. **Synthesis: the cheapest discriminator, evaluation only.** Price Oak with the *continuation* played by the oracle for the rest of the turn and the next (S/T prompt oracle on every decision after the Oak, both sides equal), against the pilot's own continuation. If Oak turns positive with a strong continuation, conversion is the bottleneck, and the route is pilot play strength broadly (search at play time, or longer self-play), not card-specific fixes. Not queued.
- **FLAG, usage:** the week went 36% → 40% in one hour (14:41 → 15:41), about 4 points an hour against a line slope of about 0.55. At this pace the week is gone in about 15 hours. 5h 30%. Hold all builders and research rounds to the minimum. Evan's bench-or-drafting decision (#480) is still the main open item.
RESEARCH CALL: is continuation play the bottleneck? Price Oak with an oracle continuation against the pilot's own (evaluation only), before any new training arm. Keep it CPU-only and small, given the usage.

AUDIT JOB PAUSED (15:42, 333-10's call after A120's usage flag): nothing is running, and all agents are held until Evan's bench-or-drafting decision (#480). Hourly job ef291c8a is deleted, to be recreated on 333-10's message when a run launches or Evan returns.

NOTE, FOCUS: DRAFTING RESUMED (Evan row 103, 2026-10-29 10:49, option (b); relayed by 333-10 at 11:08; replaces the bench focus notes). The ground truth (G1/G3 against the lists) leads again. First run: C119, the gated drafting base re-measured at seeds 5 and 6, launched 11:07 (runs/screens/C119-gate-base/record.md, log #536-538). Carry the bench lessons as context: oracle ceilings about an Energy; Oak/CS/IF lose for this pilot; continuation-play weakness untested (A120). Audit job recreated hourly at :13.

A121 · 2026-10-29 11:15 · Ground truth: C119 (the gated base re-measured, seeds 5 and 6, bands first: record 10:58, launch 11:07) is in stage 1, 8 minutes in: s5 at it 5 is 12.9 / 22.6 / 24.5, dist 12.5, mean5 12.3; s6 has no row on gt_board yet (to check next audit). Not yet readable; no new result. Thesis: drafting from the gate base with the bench lessons as context (A120: continuation play is the untested bottleneck). **Usage: 5h 22% / week 43% against a line of about 27.5%: over.** No RESEARCH CALL: C119 is the queued anchor, mid-flight.

A122 · 2026-10-29 12:15 · drafting (new result)
1. **Ground truth.** **C119 reproduces the gated fresh base on engine K (#540, bands first):** at it 29, s5 is 14.8 / 23.4 / 21.8, mean5 13.0; s6 is 13.9 / 20.8 / 25.3, mean5 13.8 (C90/C93's range 8.7-14.4). s5 meets R-repro: G1 13.0 within 4.47-15.87, and the tempo cards T4 at 1.83 copies a deck, within its Amendment-1 range of 1.24-3.34. s5 G3 0.269. s6's readout is pending. G1 is far from the target, and C91's warm anchor (6.43) is still the best.
2. **Thesis (implied by the restart):** with the gate as base, the drafting loop will move toward the lists once the pilot values tempo. No next arm is in the log yet.
3. **Antithesis (A120, untested):** the pilot's continuation play can't convert resource cards (Oak, Bill, CS, IF), so any faithful draft prices them under an Energy. The gate base will reproduce the Energy lean (s6: Energy 25.3) whatever the drafting change.
4. **Evidence.** C119 is consistent with both: a reproduction, not an effect. The bench's oracle ceilings and P10's "Oak loses for this pilot" support the antithesis.
5. **Synthesis.** A120's continuation-oracle price of Oak (evaluation only, CPU) is still the discriminator. If a strong continuation turns Oak positive, the next drafting arm should strengthen play (e.g. test-time search inside the draft's games) rather than change drafting. Not queued; research holds it (#520s, usage).
- Checks: C119 bands first, seeds run one at a time for RAM (row 73). On focus. **Usage 5h 33% / week 44% against a line of about 28%: over.**
RESEARCH CALL: before the first new drafting arm, run A120's continuation-oracle test (Oak priced with the oracle continuing, evaluation only, small). Its answer decides whether the next arm changes drafting or play strength.

A123 · 2026-10-29 13:15 · Ground truth: C119 reads R-repro at both seeds (#541, #542, banded): G1 13.00 / 13.83, T4 1.83 / 1.58 copies a deck. **The tempo deficit stays about 7 copies a deck against the lists' 9.17.** C120 (the same base on the engine build with #493's two minor faults fixed, record first) is running: s5 stage 1 passed (interim G1 12.2), and s6 is under way. A sequencer fault cost about 8 minutes (#544), now logged. Dialectic: C120 is a second reproduction, and #493's faults were on off-bench cards, so its prior is null. A120's continuation test (C118, ready) is the one that can change the next arm, and it is held for usage. **Usage 5h 38% / week 45% against a line of about 28.4%: over.** RESEARCH CALL (2-hour rule): when C120 ends, run C118 before any new drafting arm.

A124 · 2026-10-29 14:15 · Ground truth: C120 (the gated base on the fixed engine build) reads **between** (#545, #546, banded). s5 is in band (G1 11.73, T4 2.08), but s6 slid toward Pokemon after iteration 23 (G1 20.80, out of band; population Trainers 27 → 21). The two-seed mean of 16.27 is inside the band, so no effect of the fix is claimed (the fixed cards are absent from both G1 sets). Seed 7 (C120 Amendment 1, written before it runs) is at it 17: 12.3 / 24.3 / 23.3, mean5 9.6. **Flag, optional stopping:** adding a seed after a split result is fine only if Amendment 1 says beforehand how 3 seeds are read (e.g. majority in band, or the 3-seed mean). Check that the amendment states it. The drift on s6 (Trainers falling late) is the same Energy/Pokemon lean the project started with, even from the gated base. C118 (continuation test) has only its record (from 10-28 15:43), not run: held for usage. **Usage 5h 43% / week 46% against a line of about 28.8%: over.** RESEARCH CALL stays: C118 before any new drafting arm.
- A124 follow-up: C120 Amendment 1 states the 3-seed rule before seed 7 runs. If seed 7's G1 is 16.83 or less with T4 in band, the fixed build is the base and s6 a tail draw. If not, s6 and s7 are rerun on the old build. Optional-stopping flag resolved. It also adds a G1 watch to every lever's stop rule, which is good.

A125 · 2026-10-29 15:16 · Ground truth: **C120 settled by its pre-written Amendment 1 (#548, #549):** seed 7 G1 7.37 (14.2 / 25.4 / 20.4; the closest gated fresh seed yet), T4 2.58, G3 0.302. So the fixed build is the drafting base and s6 a tail draw. **New noise reference: over nine gated seeds G1 is 11.93 ± 4.20 (sd per seed), T4 2.07 ± 0.39 against the lists' 9.17.** A drafting lever needs about -6 G1 at two seeds to clear 2 SE. That is twice the header's 3-point bar (set from seed gaps of about 2), so readings from now on should use the measured 4.2. Dialectic: one seed (s7) at 7.4 and one (s6) at 20.8 from the same recipe says seed variance, not the recipe, decides most of G1. Any 2-seed lever is underpowered unless its effect is large. Long view: the tempo deficit (about 7 copies) is stable across seeds; it, not G1, is the sharper target. GPU idle since about 14:35 (no run queued; usage hold, not a stall). C118 (continuation test) still unrun. Usage: 5h reset (not in file) / week 46% against a line of about 29.4%: over. RESEARCH CALL: run C118 next (small, evaluation only). It decides whether the first lever targets drafting or play strength.

A126 · 2026-10-29 16:16 · Ground truth: not moved (best gated fresh seed C120 s7, G1 7.37; 9-seed mean 11.93 ± 4.20; T4 about 2 copies against 9.17). Nothing new since #549. **The GPU has been idle about 1h40 with no next lever recorded.** It is a usage hold, not a stall, but C118 (A122's discriminator) is still unrun. Usage 5h 0% (reset) / week 46% against a line of about 30%: over. A125's RESEARCH CALL stands (C118 next), not repeated.

A127 · 2026-10-29 17:15 · Ground truth: not moved (C120 s7 G1 7.37 best; 9-seed mean 11.93 ± 4.20; T4 about 2 against 9.17). Nothing new since #549 (about 2h15); GPU idle. Usage 5h 0% / week 46% (flat for 2 hours) against a line of about 30.5%: over, though not rising. RESEARCH CALL (2-hour rule): run C118, the continuation test (small, evaluation only). It decides whether the first drafting lever targets drafting or play strength, and the week is not climbing.

Note after A127 (17:16, from research): C118 stays held. It needs 333-10's go under an explicit usage hold ("Keep C118 and (d) held"), asked twice (11:2x, 14:38); 333-10 shows as waiting, possibly on Evan. Research's reading at 17:16 is week 50% / 5h 27%; this session's file read week 46% / 5h 0% at 17:15, so the writers disagree again. Take the higher: **week 50% against a line of about 30.8%: 19 points over.** The hold is correct. The auditor won't repeat the C118 RESEARCH CALL while the hold stands; the open item is 333-10's/Evan's, and the next audits record it in one line.

A128 · 2026-10-29 18:15 · Ground truth: not moved (C120 s7 G1 7.37 best; 9-seed mean 11.93 ± 4.20; T4 about 2 against 9.17). Nothing new since #549; the GPU is idle under the usage hold (C118 held for 333-10/Evan), so not a stall. Usage 5h 29% / week 51% against a line of about 31.3%: over (+5 points in 3 hours with nothing running). No RESEARCH CALL while the hold stands (A127 note).

A129 · 2026-10-29 19:15 · Ground truth: not moved (C120 s7 G1 7.37 best; 9-seed mean 11.93 ± 4.20; T4 about 2 against 9.17). Nothing new since #549; no runs, no log entries in about 4 hours. **FLAG, usage burning with nothing running: 5h 29% → 52% in one hour, week 51% → 54% (line about 31.8%, 22 points over).** Some session is spending heavily without logging anything. Check which (ListAgents / the perch), and pause idle loops. The 5h window resets about 20:10. No RESEARCH CALL (the hold stands).

A130 · 2026-10-29 20:16 · Ground truth: not moved (C120 s7 G1 7.37 best). Nothing new since #549 (about 5h); no runs; the C118 hold stands. Usage: 5h reset at 20:10 (not in file) / week 54% against a line of about 32.3% (flat this hour, over). A129's burn flag is unanswered by 333-10. No RESEARCH CALL (the hold stands).

A131 · 2026-10-29 21:15 · Ground truth: not moved (C120 s7 G1 7.37 best). Nothing new since #549 (about 6h); no runs; the C118 hold stands (waiting on 333-10/Evan). Usage 5h 0% / week 54% against a line of about 32.8% (flat, over). No RESEARCH CALL (the hold stands).

NOTE (21:56, 333-10 21:55): the usage spike from 18:15 to 19:15 is probably Evan's own use elsewhere on the account (the desktop app has been open since 12:57; the loop supervisor is paused; only the 4 CLI sessions run). Unverified. Runs resume: Evan row 105 (21:56) says don't wait for permission, so C118 and the drafting levers chain back to back. The audit job moves to every 2 hours at :13 on even hours (new job id in chat).

A132 · 2026-10-29 22:43 · drafting resumed (new result)
1. **Ground truth.** Not moved: C120 s7 G1 7.37 best; 9-seed mean 11.93 ± 4.20; T4 about 2 against 9.17. C121 (L-draft: the gated base with P9's per-turn discount in the drafting loop's pilot, seeds 8 and 9, banded first, with a G1 watch) is running: s8 at it 13 is 13.3 / 21.3 / 25.3, mean5 13.3; s9 at it 2, mean5 10.8. Not readable yet. C122 is recorded.
2. **Thesis:** pace pressure in the drafting loop's pilot will pull drafts toward tempo cards (C121).
3. **Antithesis (A120's) is weakened. C118 reads R-not-conversion (#552, #553, banded):** a two-turn search continuation moves Oak from -0.055 to -0.008 (difference +0.047 [-0.015, +0.109], not significant), and the drawn cards aren't put into play more often. So short-horizon play strength isn't the bottleneck either. What remains untested: whether drafting itself, given a pilot that values tempo cards at about an Energy, has any gradient toward them at all. If the cards' prices are at about 0.50, the draft is indifferent and the gate keeps whatever it starts with.
4. **Evidence.** For the antithesis: every per-card price sits at 0.43-0.52, so a faithful draft has almost no signal to add them. For the thesis: P9's discount changed how games end (knockouts 1.13x) but not Trainer play.
5. **Synthesis.** C121 reads it directly on G1/T4 against the 9-seed noise (it needs about -6 G1 or T4 well above 2.07 ± 0.39). Running, banded; no new test needed.
- Checks: C118 timed a 4-state pilot first (working rule 4); C121 bands first, with the G1 watch. **Usage 5h 11% / week 56% against a line of about 33.5%: over.**
No RESEARCH CALL: a banded result landed (C118) and C121 is mid-flight.
