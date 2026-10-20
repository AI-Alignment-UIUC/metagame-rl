# The lab: keep training, test changes as short branches (2026-10-18)

Why (log #70–82): the pilot screens could not rank anything. They stopped at 40–80 iterations while the
pilot was still improving (+55 Elo from 40 more iterations, #82), their seed and rerun noise (6–20 and ±15 Elo) was as
large as every effect (#74), each from-scratch arm spent about 25 iterations learning to end games (#70–71), and the
6–15 hour chains decided only at their end and were cut off by a shutdown and by sleep (#72, #77).

## Constants (Evan, 2026-10-18)

- **The method must carry over to other card games.** A change may use only what any card game's environment gives:
  cards as features and rules text, the legal options, the result (and a game's own score at the end, here the prize
  margin, which every TCG has in some form). No card-specific rules, no hand-made features. Each card states this.
- **The ground truth is rediscovering the meta by playing the decks it drafted, with the drafting reusing what the
  pilot learned.** So the main line is `rl/metagame.py` itself: one pilot trained only on the decks the draft head
  drafts, and a draft head that reads every deck through that pilot's encoder (`rl/draft.py`). Pilot training on fixed
  decks (`rl.train`) is no longer the main line. The archived lists are the answer key, for evaluation only.
- **The lab uses at most a third of the GPU**, so Evan can use the rest: `RL_GPU_SHARE=0.333` caps every process it
  starts, in memory (the per-process fraction, about 5.4 of 16 GB) and in time (training and the inference server rest
  twice each step's GPU time). `RL_CPU_THREADS=10` leaves 8 workers, so that with a job of Evan's the machine stays
  under the 16-thread cap (CLAUDE.md).

## How it runs (`rl/lab.py`)

- **Main line.** `runs/lab/main` continues meta-99 from its 150 iterations (pilot-v2, then 150 iterations on its own
  drafted decks from random ones; #69) in segments of 10 iterations (one turnover period). It never stops, so
  training makes progress even when every experiment fails. Every 40 iterations: the answer key under pilot-v2 (the same
  measure as #69, so the trend is comparable), and SimpleBot.
- **Branches.** A card forks the main line's whole state at a segment boundary (pilot, optimizer, draft head,
  population, random state), changes one thing, and runs the same 10 iterations. The control is the main line's own
  segment, so it costs nothing. New modules start as the identity or at zero, so a branch starts as the main line plays.
- **Decisions.**
  - A pilot card is decided by the branch's pilot against the main line's, on fixed deck pairs from both populations
    (both pilots on both decks, both seat orders, the same deals), with a sequential test (H0 Elo ≤ 0 against
    H1 Elo ≥ elo1, α = β = 0.05, at most 6,000 games). The gate: on the archived lists, not clearly worse.
  - A meta card is decided by the answer key of both populations, both played by the main line's pilot, with a rule
    written into the card before the run. The gate: the pilot is not clearly worse.
  - Slow-payoff changes run 2 segments, and only "clearly worse" stops them after the first.
  - A card that passes is adopted (the main line goes on from the branch), one at a time. A card that ends undecided is
    closed, not extended. Cards still running from an earlier fork when a card is adopted are rebased: closed and queued
    again (`<id>-b`) from the new main line, since their control is gone (#87).
- **A/A first.** Two cards with no change (same seed, and reseeded) measure the noise a branch sees. elo1 and the meta
  thresholds are set from them, and they are not changed after a result is seen. The rule, written 2026-10-19 before
  either A/A card was measured: forks share no random numbers (#83), so a branch with no change is itself a different
  pilot, and the sequential test controls only the evaluation's noise, not that one. So, over the two A/A cards,
  - the training spread σ = sqrt(max(0, mean(Elo²) − mean(SE²))) on the drafted panel (SE = the 95% interval's width / 3.92),
    and elo1 = max(15, 2σ), rounded up to a multiple of 5;
  - a meta rule's min_gain = max(0.03, 2 × the root mean square of the two cards' archived_mean differences from the main
    line), rounded up to 0.01; staples and overlap thresholds the same way if a card uses them.
- **Robust to the machine.** Every step resumes from files; a `runs/lab/STOP` file ends it cleanly after the current
  iteration; it keeps the PC from idle sleep and waits when free RAM or GPU memory runs short.
- **Me.** I watch `runs/lab/events.jsonl`, write a log entry per decided card or milestone, and keep the queue at least
  two cards deep.

## Using the answer key without fitting to it

Choosing changes by the 2000 answer key makes 2000 a development set: with enough cards, the lab could fit its one
recorded field. So pilot cards are decided on drafted decks (no human input), the archived lists are only a gate, and
the record of each meta card says how many times the answer key was consulted. The test of the method is the
held-out games: Worlds 2005 (Phase B), whose answer key no card may read, and Magic later.

## Program-level stall rule

If the main line gains less than the A/A noise over three milestones in a row and the last five cards failed, the lab
stops queueing small changes and moves to a larger one (a bigger pilot through distillation, a league, or a different
draft procedure), and I report it.

## First cards

1. `001-aa-same`, `002-aa-reseed`: the noise.
2. Pilot: value cross-attention trained with the trunk (`value_query 4`, parked since #77); slot binding (the only arm to
   clear 95% once, #74); 2 PPO epochs instead of 3 (an iteration's PPO is about half its time); auxiliary value heads with
   game-general targets (decisions until the game ends, the opponent's next action type), still to build.
3. Meta: a draft reward of the result alone (`--draft-margin 0`, more general), 6 swaps a draw, turnover 0.3.
