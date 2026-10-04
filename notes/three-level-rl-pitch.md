# Three-Level RL for Trading Card Games: Move, Game, Metagame

Draft pitch, 2026-09-20. Source material: `tcg-rl-research-notes.md`. Every number below is measured in those notes unless marked as an estimate.

## The one-line version

Give an agent only a card pool and the rules. It learns to make good moves, to win games with any deck, and to build the decks worth playing. We then check whether it rediscovers a real historical World Championship metagame.

## Why this is a good problem

Trading card games are three decision problems stacked on top of each other. Most game-playing RL solves one. Chess and Go have no deckbuilding. Draft bots and deck recommenders do not play. Nobody has closed the loop where play skill decides which decks are good and the decks in the field decide which play skills matter.

The stack also comes with something rare in RL research: an external answer key. Humans have played the outer game for decades, and the results are archived. Worlds 2013 and 2014 decklists and placements are public. An agent that starts from nothing and lands on Blastoise/Keldeo, Darkrai, and Yveltal/Garbodor has shown something a win rate against its own past checkpoints never can.

## The three levels

| Level | Decision | Horizon | Method | Signal it receives |
|---|---|---|---|---|
| **Move** | Which card, which target, which search pick, inside one turn | One prompt | Transformer over card tokens, verb head plus pointer head over legal candidates | Policy gradient and value from the game level |
| **Game** | How to pilot a fixed 60-card deck through a full match under hidden information | 70 to 190 decisions | Population self-play, one deck-general policy with a value head | Win or loss |
| **Metagame** | Which deck to bring, given what everyone else brings | One tournament field | Deck-edit policy inside a PSRO loop, rectified-Nash meta-solver, quality-diversity archive | Matchup table produced by the game level |

**Move level.** Every visible card is a token. Multi-step effects such as Ultra Ball become a sequence of small prompts, each a softmax over the real candidates. There is no fixed action table, no hand cap, and no truncation. The same network handles a 41-card pool and a 900-card pool.

**Game level.** One policy plays every deck, conditioned on its own decklist and the opponent's. It trains against a population, not only against itself, so it does not develop private habits that a new opponent punishes.

**Metagame level.** Deckbuilding is an edit policy: start from a deck, make 10 to 20 remove-and-add edits under the format's construction rules. The target is a mixture of decks, not one best deck, because card metas are non-transitive. Exploiter episodes produce counter-decks. A MAP-Elites archive over deck descriptors keeps archetypes alive and doubles as the rediscovery measurement.

## The idea that ties it together

All three levels share one card representation, and information flows both ways.

- **Knowledge flows up.** The play network's value at turn zero, averaged over opening hands, is already a matchup predictor. It was trained on real outcomes and shaped by every mid-game state. The deck builder uses the change in that value as its edit reward. Attention weights that learned Blastoise needs Water Energy during play are reused to score candidate cards during building.
- **Pressure flows down.** The meta mixture decides which matchups the play policy trains on. New decks get piloting time before their matchup row is trusted, so a deck is never judged by a pilot who cannot play it.

Card embeddings built from structured features plus rules text let a new card get a usable representation on day one. That is what makes transfer to unseen cards and to drafting formats plausible.

## What exists today

- A working Python simulator with full 60-card decks, Mega Starmie ex against Mega Lucario ex, 41 distinct cards. It runs about 13,000 decisions per second single-threaded, so speed is not the bottleneck.
- A diagnosis of why training stalled. In about a third of decisions the agent must choose between cards its observation cannot tell apart. Half of heuristic-play Ultra Ball searches cannot reach every Pokémon in the deck. The problem is the encoding, not 60-card complexity.
- A specified fix: an identity-indexed state of 576 floats and roughly 100 actions, against 295 actions today, with strictly more information.
- An engine survey. ryuu-play has about 890 cards from the 2010 to 2015 era and the right architecture. Two archived Worlds Blastoise/Keldeo lists are 57 of 60 cards buildable in it. Seven era archetypes are buildable. Team Plasma is missing.
- A reference point from Magic: MageZero already tokenises full game state and runs AlphaZero-style search on XMage.

No trained agent at any level has been evaluated yet. The contribution so far is the diagnosis, the design, and the ground-truth plan.

## Milestones

1. **Move.** Identity-indexed encoder on the two existing decks. Success means the agent beats the built-in heuristic, which the current encoding could not do reliably.
2. **Move, scaled.** Tokens and pointer heads on the same decks. Must match or beat milestone 1.
3. **Engine decision.** Measure ryuu-play's step rate, then either fork it or port its design to Python.
4. **Game.** One deck-general policy on four historical archetypes with per-year legal pools. Success means it reproduces the known matchup directions.
5. **Metagame.** The PSRO loop with diversity mechanisms. Success means historical archetypes appear in the equilibrium support from a cold start.
6. **Transfer.** Builder rewarded by the play value head, compared against a standalone matchup model.
7. **Humans.** Fixed lists against Legacy-format players on a ryuu-play server, about 200 games per opponent pool.

Each milestone is a result on its own. Milestones 1 and 2 need one laptop.

## Evaluation

| Level | Primary check | Secondary check |
|---|---|---|
| Move | Puzzle positions with provable answers: lethal, deck-out avoidance | Agreement with transcribed Worlds finals decisions |
| Game | Win rate against heuristic, SimpleBot, and large-budget search | Live human play on fixed lists, seats swapped |
| Metagame | Archetype rediscovery by card overlap with archived Worlds lists | Matchup directions against era write-ups |

## Risks, stated plainly

- **Coupling.** A weak pilot undervalues setup decks. The discovered meta reflects the agent's skill ceiling. We treat which archetypes appear as play improves as a finding in its own right.
- **Engine bugs become meta bugs.** Historical lists double as regression tests.
- **Compute at the top level.** One new deck row in a 40-deck population is about 8,000 games at 200 games per pair. Only new rows are measured each iteration.
- **Human metas are not equilibria.** Archetype rediscovery is the robust comparison. Meta share percentages are not.
- **Coverage.** The open 2010 to 2015 pool lacks Team Plasma, so "Worlds 2013 from scratch" holds only for the buildable subset.

## Open choices for this pitch

These change the framing and are marked so they are easy to revise.

- **Audience.** This draft is written for a technical reader such as a collaborator or advisor. A funder version would lead with applications: game balance testing before a set ships, and draft or deck assistants.
- **Drafting.** The top level here is constructed deckbuilding. Drafting is the same edit policy with a pack-sized candidate set and hidden opponent picks. Magic Limited has 17lands data as ground truth. Say if drafting should be a headline result instead of an extension.
- **Level boundaries.** "Move" is read here as the single prompt-level decision and "game" as the full-match policy and value. If "move" was meant as in-turn search such as MCTS, the table's Method column changes and nothing else does.
