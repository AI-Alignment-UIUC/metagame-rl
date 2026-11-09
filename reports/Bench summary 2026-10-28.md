# Bench summary, 2026-10-28

*Research agent, for Evan's morning decision (auditor A107 via 333-10). "Measured" means from a logged run, with its
game count. "Estimated" means arithmetic or judgment.*

## The decision

**I recommend (b): resume drafting with the gate as base, and read G1 plus the tempo-card counts.** The bench found
nothing more a pilot can give these Trainers. Even oracle play prices them at about an Energy, and 16 hours of bench
arms produced 0 per-card effects that met their bands on two seeds (the auditor's count).

## What the bench tested

The setup is four practice lists. A card's price is the list's win share against a copy with that card turned into
basic Energy, the same pilot on both sides, at 256 games a pair. The goal was every Trainer at 0.50 or above.

| Test | Result (measured unless marked) |
|---|---|
| Baseline, start and arm 0 (plain PPO, 30 min; #417) | Every focus card prices under an Energy: PlusPower 0.44-0.45, Gust 0.44-0.47, Item Finder 0.43-0.46, Scoop Up 0.45-0.46, Computer Search 0.44-0.46. Arm 0 plays stronger (0.615 against start) but prices don't move. |
| P2, P1, P1b, P1c (card identity and option binding) | P2 dead. P1 failed its fidelity gate. P1b's binding was live but Computer Search's answers were worse (one seed). P1c was killed by the KL rule at both seeds, likely the fresh-optimizer effect found later. No gain. |
| C98, C99, C102, C105 (Computer Search) | The oracle's answers add +0.05 (to about 0.46-0.54). Timing adds nothing; discards add nothing. Its main target's extra copy is worth an Energy (0.48 ± 0.03). Capped at about an Energy. |
| C103 (Energy count) | The trained pilot is about lists-optimal in Energy count on these lists. |
| C106, C108, C110, C111 (PlusPower) | Oracle timing lifts it from about 0.44 to 0.51-0.53, at every pilot strength. The learned policy runs backwards: it plays PlusPower when it can't attack. The state carries what the decision needs (AUC 0.92 at the decision input, mostly the Defender's HP), so the failure is learning, not representation. |
| C107 (Gust) | Oracle targets add +0.01-0.02, so its target choice isn't the problem. |
| C109 | Confounded by design (my error). No claim. |
| P5, P5b, P5c, P5d (the pilot's own branches as PlusPower's training signal) | Catching rose from 0.003 to about 0.07 knockouts a game against the oracle's 0.17, then plateaued (P5d). Prices 0.46-0.49; no seed pair cleared its band. The pace is bound by KL: 58-75% of update steps cut. |
| P7 | Written, not run: the literature round showed it can't help. |
| P8 (the same signal for every Trainer, no card list) | No card up. One seed survived: M 0.448 against arm 0's 0.461, and a weaker pilot (head-to-head 0.421 ± 0.015). |
| P4, P6, C104 | Not run (low priority, or gated off). |

## What stands

- **The gate's G1 effect (C93, measured, 4 seeds).** From fresh decks, gated drafts stay closer to the human lists:
  G1 −7.6, 95% CI [−11.9, −3.3]. It is the only replicated ground-truth effect so far.
- **C91's G3 is 0.57 (measured).** C91's best 12 drafted decks beat the human lists in 57% of decisive games under
  the C49-sd pilot, while carrying 3-4.5 more Energy. This may partly reflect that pilot's weaknesses.
- **Oracle ceilings at about an Energy (measured):** Computer Search 0.50-0.54; PlusPower 0.51-0.53; Gust targets
  +0.02.

## What it means for the ground truth

- **The pilot can't explain much of the drafts' Trainer deficit.** The drafts are short of the lists by about 2.7
  PlusPower, 2.4 Gust, 2.0 Item Finder and 1.7 Scoop Up a deck (A99). On this engine, perfect play of those cards is
  worth about an Energy each, so a better pilot buys at most +0.05-0.08 per card (estimated from the oracles). That
  makes a drafter close to indifferent, not keen on four copies.
- **By your rule the lists are optimal,** so the deviation must come from elsewhere in the pipeline. A correct engine
  plays the same game, so it can't reward anything different. The candidates are:
  - engine bugs;
  - environment rules that differ from tournament play;
  - what this pilot can exploit (G3 0.57 says Energy-heavy decks beat the lists under it);
  - how drafting explores;
  - the bench's own framing: each list is priced against its own copy, not against the 2000 field.

  *(Corrected 2026-10-28 after Evan's question; it first read "what the engine rewards".)*
- **A pipeline signal for the engine audit (measured in P5c's evaluation, seed 91, 768 games):** 622 games (81%) end
  on the turn cap and 26 (3%) by Prizes. At the real STS, time was reached in about 5-25% of Swiss games (C02). Fast
  human decks took six Prizes in about 13-14 engine turns (C02); our cap is 20-45.

## The strongest case for (a)

- The bench is the only place a cause can be isolated cheaply (30-minute arms, 256-game prices). Drafting is long and
  noisy: G1 needed 4 seeds.
- PlusPower's learning gap is real and measured (0.44 against the oracle's 0.52). A redefined target, "close the gap
  to the oracle ceiling", is reachable.
- P5d's 0.485 at one seed hints that progress is slow, not absent.

## Why I still pick (b)

- The ceiling caps what (a) can win, at about +0.05-0.08 per card (estimated).
- Every route tried plateaued or harmed.
- The ground-truth metric lives in drafting, where the gate's effect is the one result that replicated.
- Reading G1 together with the tempo-card counts shows directly whether the deficit moves. If it doesn't move, that
  points to engine bugs, environment rules or the field rather than the pilot. A redefined bench can still check a single pilot question
  when drafting raises one.
