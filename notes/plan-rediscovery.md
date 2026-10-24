# Plan: rediscovering the human metagame (2026-10-19, for Evan's review)

> **Superseded 2026-10-22 by `notes/method.md`** (approved by Evan, `notes/evan-requests.md` row 39, log #152). Kept as
> history; its approved targets (Evan, row 10) live on in the method's scorecard (§3).

The goal: from random decks, with nothing human in training, the method drafts and plays a metagame that matches the
2000 STS human field. Then the same method, unchanged, does the same for Worlds 2005 (held out) and later Magic.
Evan's comments are in `notes/evan-requests.md`; the evidence is in the progress log (#1–94); every change is tested in
the lab (`rl/lab.py`, `notes/plan-lab.md`).

**Ground-truth rule (Evan).** The human lists are ground truth. If the drafted decks are far from them (for example,
far more Energy), the drafting or the playing is learning something wrong. A test where basic Energy beats a Trainer
means the pilot misplays the Trainer. The human lists are used for evaluation and diagnosis only, never in training.

**The gap today**

| | Pokémon | Trainers | Energy | Staples (of 10) | Archetypes at overlap ≥ 0.5 |
|---|---|---|---|---|---|
| 24 human lists (median) | 13.5 | 28 | 18 | 8.5 | 8 archetypes |
| Drafted best decks | 20 | 11 | 29 | 2–5 | 0–1 |

**Why (log #92).** The pilot does not set up before it attacks. It solves win-this-turn puzzles that need only an
attack at 86–94%, but PlusPower-then-attack ones at 31%, random's rate. This is true of every pilot, including ones
trained on the human lists, and its inputs and the cards themselves check out. So every Trainer except Oak and Bill is
worth less than an Energy to it. The drafting learns from that pilot, judges each draw by the one game in which the pilot
first plays it, and its incoming choice has collapsed, so it trades Trainers for Energy and the meta slows down, which
makes setup worth even less. The fix starts at the pilot.

## Scorecard (evaluation only, every lab milestone)

| | Measure | Now | Target |
|---|---|---|---|
| Pilot | Each Trainer group's value on the human lists (draw / search / disrupt / tempo, against an Energy copy) | 0.67 / 0.42 / 0.46 / 0.41 | all > 0.55 |
| Pilot | Win-this-turn puzzles: attack-only / Trainer-first / PlusPower | 90 / 60 / 31% | ≥ 90 / 85 / 90% |
| Pilot | Strength against SimpleBot on the human lists | 0.82 (main line at 240, ± 0.034; pilot-v2 0.82) | ≥ 0.90 |
| Decks | Median Pokémon / Trainers / Energy; staples a deck; archetypes at overlap ≥ 0.5 | 20 / 11 / 29; 2–5; 0–1 | within 5 of 13.5 / 28 / 18; ≥ 7; ≥ 3 |
| Decks | The draft head's incoming entropy; the swing in median Trainers over 40 iterations | 0.2–1 nats; 2–15 | ≥ 2 nats; ≤ 5 |
| Meta | Best decks against the human lists, under a pilot that passes the pilot rows | 0.48 (pilot-v2), 0.62 (SimpleBot) | ≥ 0.5 |

## Three stages

### Stage 1: the pilot plays the human field's cards correctly
1. **Evan's pilot ideas, tried fully (running).** Memory for the pilot in three forms (history tokens, attention
   memory, GRU) and the deck-free board encoder with cross-attention to the deck, as lab cards.
2. **Lookahead within the turn.** First measure play-time search over the current pilot on the puzzles and the
   Trainer-value panel (about an hour). If it fixes setup, train the policy toward the search's choices (expert
   iteration), with lines scored by the game's own outcome within the turn (Knock Outs, prizes, a won game) and the
   value.
3. **Credit and exploration within the turn**, if step 2 falls short: λ = 1 inside a turn (0.95 across turns), prize
   shaping kept on (it is potential-based), and entropy 0.02.

*Done when* the pilot rows of the scorecard meet their targets.

### Stage 2: the drafting finds the human deck shape
1. **Practice before a draw counts (Evan; running).** Seasons of 5 iterations with 4 candidates a deck, and of 10
   iterations with 2 candidates: the pilot trains on a deck's candidates before their results reach the draft head.
2. **Draft with the Stage 1 pilot**, with its search if it needs one, so a deck is judged by a player that can use its
   cards.
3. **Keep the draft head exploring:** a floor on its incoming entropy, and the draft reward from the result alone if
   that replication passes.

*Done when* the deck rows meet their targets.

### Stage 3: rediscover from scratch and test on held-out games
1. **The headline run.** The adopted recipe from random decks and a fresh pilot, scored on the whole scorecard and
   written up as a numbered result.
2. **Worlds 2005, unchanged** (Phase B). Nothing from 2005 is ever used to choose a change.
3. **Magic**, with the same method.

## How the loop runs
- The lab computes the scorecard at every milestone. It works on the earliest stage whose targets are not met;
  cards from later stages still run, but they are read as secondary until the earlier stage passes.
- Evan's ideas go first and are tried fully, in their strongest version plus a variant. Every card states its
  generality and the scorecard row it must move, with its threshold set from an A/A spread before it runs.
- Drafting cards also have to keep their best decks no more than 16 cards (the A/A spread) further from the human
  shape than the main line's (log #102).
- Every 3 adoptions, a from-scratch check run, so the method rediscovers on its own and is not just a long-trained
  main line. If the largest gap does not shrink over three milestones, the next step of that stage starts.

## Questions for Evan
1. Prize shaping kept on rather than fading to 0 (Stage 1, step 3)?
2. The game's own score (Knock Outs, prizes) inside the turn-level search (Stage 1, step 2)?
3. Pilot changes decided on the puzzles and the Trainer-value panel, which are built from the human lists, with 2005
   held out?
4. Are the targets the right bars?
