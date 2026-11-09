# Round 2 (audit A44's RESEARCH CALL; 333-10's go at 21:16): the gap between drafted decks and the lists beyond prompt answers

Two Haiku lean-readers, about 21:16. Sources are abstract-, snippet- or secondary-level unless marked.

## A. Per-card signals for the draft from the system's own games
- Games-in-hand win rate and "improvement when drawn" (17lands, via secondary articles) are biased.
  - Selection: strong decks draw more cards.
  - Survivorship: long games see more cards, which could flatter Energy here.
  - "Embarrassingly Causal" (arXiv 2604.18314, abstract only) finds substantial confounding and post-treatment
    conditioning in such statistics.
- Difference rewards and COMA (Foerster 2018) credit one component by the global result minus the result with it
  replaced. In our terms: play the old and the edited deck on the same seeds and credit the paired difference.
- No source shows per-card ratings beating whole-deck fitness under noise. Hearthstone deck evolution (de Mesentier
  Silva 2019) is abstract-level only.

## B. Draw engines in deck-building games
- Halawi et al. 2024, Dominion benchmark (arXiv 2405.06846, read in full):
  - A self-play Rainbow DQN beat every heuristic except the draw-and-chain engine. Against Provincial's engine the
    DQN bot lost 558 of 1,000.
  - It played money strategies, "buying Duchies too early", which the paper puts down to the engine combination "not
    being explored during training": our Energy-over-Trainers in another game.
- Gerigk & Engels, AIIDE 2023 (abstract): learning card combinations needs an algorithm that finds "a precise strategy
  while ignoring simpler suboptimal policies with higher immediate rewards"; training changes gave human-like
  strategies.
- Slay the Spire (a blog, snippets): card picks barely moved the agent until their reward scale was raised; floors went
  from 12.4 to 14.7.

## Turned into
C90 (`runs/probe/C90-pairedselect/record.md`): the draft's `--select` paired with common random numbers, so a deck
moves only when a candidate beats it by more than 1 SE on the same opponents and deals. It is read on the ground
truth (G1, G3) against C85 as the control.
