# C02 record: how many engine turns a 2000 STS round allowed (written before any reading, 2026-10-22 ~22:05; method §10; log #161)

    C02 · outside research (one agent, Q1 and Q2 first) · N1, N12 · H03, H61, H71 · rivals R-fast / R-slow / H-pilot-slow /
    R-unknown · Evan: yes (row 41: "Sure try using that time limit", D1 option (a)) · no machine · ≈ 3 dh ·
    rules 1-3: facts that define the game's rules enter only as the rule's parameter, fixed before any run; which decks
    won is never used for any parameter; MTG: the same question for its round length (50 minutes)

**Why.** Evan approved the 2000 round rule for training and judging (row 41). Its one parameter is T, the engine turn
(both players' turns counted) at which a 20-minute round is cut. D2 forbids setting T by its effect on distance to the
human lists, and #156-#159 show T alone moves the verdict (J2 on set C crosses 0.5 at T 44.6, on set A at 55.9), so T
must come from the round's documented length.

**Formula, fixed now.** T = (R − O) / s, with R the round length in seconds (1,200 if 20 minutes is confirmed), O the
time before the first turn (shuffling, drawing 7, mulligans, setting Prizes and Basics; prior 60-180 s) and s the mean
seconds per player-turn in Base-Jungle-Fossil-Rocket play (prior 20-60 s). The prior gives T in about 17-57. A Prize
decision at time is applied when game turn T + 1 would begin (the turn in progress is finished), unless the 2000
procedure documented otherwise (then the engine follows the documented procedure, logged before any run).

**Mapping, fixed now.**
- If ≥ 2 independent sources bound s (or report turns per round directly), the reported range [a, b] of T is the
  per-game draw: each training and judged game gets T uniform on the integers a..b (D2 option (iii) with a documented
  prior). A single source gives the same draw, flagged as one-source.
- If Q1 or Q2 yields no primary source within its box (R-unknown), T is drawn uniform on 20..45 (Π, H71's prior,
  registered before #156 was read).
- C13's whole W(J, T) curve stays reported either way; the draw is never narrowed after a verdict is seen.

**Bands (rivals).** R-fast: s and O put T at or below 50 and rounds were often reported as ending at time. R-slow: T at
or above 60, or time rarely reached. H-pilot-slow: human Prize wins with Haymaker or Wigglytuff in about 12-20 engine
turns (our lists' Prize wins take 34-41 engine turns). R-unknown: fewer than 2 independent sources for Q2.

**Kill.** A 3-hour box for Q1 and Q2; a question with no primary source after 45 minutes is recorded as unknown.

**Distinct.** H03's and H61's outside-research variants were never run; #139 used an unknown cut; #147 read T 50-60
after the verdict was seen.
