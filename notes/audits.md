# Audits of the other agent

Evan, 2026-10-24 17:08: "audit the other agent for whether they are stuck in a local minima with their experiments or
truly trying a new experiment", every 30 minutes. One numbered entry per audit, newest last. The auditor only reports:
it never edits `ar/`, the progress log or runs. Each entry covers the ar/ 5-minute loop (`ar/results.tsv`) and the
planning session (progress log, `runs/dayplan`, `runs/probe`).

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
