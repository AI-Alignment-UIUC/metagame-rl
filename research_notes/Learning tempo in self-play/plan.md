# Deep-research plan: how a self-play pilot learns human-pace tempo without human priors (A136, written 2026-10-30 08:44 by `date`)

**Status:** held for usage (week over the line from 58% at 00:54 to 92% at the 11-03 08:00 reset; #588). Launch through
`anthropic-skills:deep-research` at the smallest breadth (one researcher plus the report writer) once the week is under
the line, or when Evan or 333-10 releases it.

**Question.** In the STS 2000 engine (audited faithful, #493-#496), every pilot we have needs 19-32 own turns to take six
Prizes against a passive opponent, where a scripted line takes about 9 (#505-#520). Games take about 50 turns, so long
games end by deck-out or on time, and draw and tempo Trainers price at or under an Energy for every player, search and
oracle-timed play included (#586). What general, prior-free methods make self-play agents learn to win fast (tempo),
and escape slow, passive or draw-seeking equilibria, in card games or other games?

**Already tried here (don't re-propose):** a per-turn discount, 0.98 on the bench (P9) and 0.98 / 0.95 in the loop (C121,
C124); forced Trainer exploration (P10); one- and two-turn search (C59, C118, C122); oracle timing (C111); persistent
prize shaping (lab 010, −31 Elo, #106); branching at PlusPower decisions (P5-P8); longer drafting (C123, C125); the Prize
margin in selection (C128).

**Pilot facts to give the researcher:** no payable attack on 41-45% of turns; a short Bench (full on a quarter to two
fifths of attacks); PlusPower on about 0 attacks; Oak and Bill held 79-96%; endings in the loop are about 51% no-Pokémon,
38-49% time and 6-12% Prizes; the 2000 round rule pays a win 1, a time win 2/3, a draw 1/3.

**Look for:** literature and practice on agent passivity and turtling (AlphaStar, OpenAI Five, fighting and card-game
bots); game-length effects in self-play (AlphaZero and MuZero discounts, MCTS draw bias); win-speed rewards that keep the
objective (time-to-win terms, horizon curricula, opponent populations or exploiters that punish slow play, PSRO-style
best responses); and CCG AI (Hearthstone, LoCM, MTG Forge) on tempo or aggro play learned without hand-built heuristics.

**Deliverable** (research_notes/Learning tempo in self-play/report.md): 2-3 proposals ranked by evidence and cost. Each
gives the change, its rivals and prior, bands written before the run, a kill rule, runtime (30-minute stages) and the GPU
queue slot, read on the ground truth (G1 and T4 against the lists) and the pilot's own-turns-to-six-Prizes. Then the
top one is handed to implementation as a queued record (Evan's rows 82, 87).
