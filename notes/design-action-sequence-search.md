# Design: search in action-sequence space (learned model, Gumbel MCTS)

*Draft, 2026-10-09. Status: proposed, nothing built. Follows log #50 (psearch), which supplies the
engine-grounded reference this design has to match.*

## Why

The pilot is the bottleneck for deck building (logs #36, #42, #46): a weak pilot gives decks that
all score alike, and a biased value sends the search into an Energy flood. The ceiling test (log #49)
shows how much a better move choice is worth: pilot-v2 wins 82.9% greedy and 97.6% best-of-9 on the
same 960 deals (an overestimate: later shuffles follow the actions taken, so some of those wins are luck). psearch recovers part of that at play time by cloning the engine, re-dealing hidden
cards and finishing the turn with the greedy pilot. Two limits:

- **It needs a cloneable engine.** ryuu-play clones cheaply; MTG engines (Forge and similar) don't,
  and re-dealing hidden cards by hand is game-specific.
- **It only helps at play time.** The network itself does not get stronger.

The proposal: plan in the model's own action-sequence space, MuZero-style, with a causal
transformer as the dynamics model, and use the search's visit counts as policy targets (expert
iteration), so the search improves the pilot itself.

## Model

One sequence per player's view of the game, from a root:

```
[root state tokens][a1][o1][a2][a3][o3] ...
```

- **Root state tokens** are the current encoder's input (env/tokens.js: GLOBAL, 12 SLOT tokens, card
  tokens with counts). They attend to each other in both directions, as now.
- **Action tokens** use the existing candidate encoding `[verb, card, slot1, slot2, name, extra]`
  (rl/token_model.py), plus a side embedding (mine / opponent's). Each attends to the root and to the
  tokens before it: a prefix-LM mask (bidirectional over the root, causal after it).
- **Outcome tokens** (`o`) carry what the acting player observes after a stochastic action: the
  card ids drawn or searched (as card tokens, so unseen cards still have embeddings), coin-flip
  results, and the opponent's revealed cards. Outcome tokens make chance explicit. The search
  samples them at chance nodes instead of learning abstract chance codes as Stochastic MuZero does,
  because here what a player observes is known and card-shaped.
- **Re-grounding.** In real play the root is re-encoded from the true observation at every real
  decision; the sequence only extends inside the search tree. Error therefore compounds only over
  the tree's depth, not over the game.

Heads at every action or outcome position:

| Head | Predicts | Trained on |
|---|---|---|
| policy | next action: a pointer over the candidates where the legal set is known; otherwise a factored head (verb, then card, then slots) | PPO now; search visit counts later |
| value | game result from the actor's view | game outcomes (real only) |
| legality | whether a proposed next action is legal | the enumerator's legal set (verified against the engine, log #2–9) |
| chance | distribution of the next outcome token | logged outcomes |
| consistency | the encoder's pooled vector of the real state at that point (stop-gradient) | logged states (EfficientZero's loss) |

**Known weak spot: slot references go stale.** A candidate's slot reference gathers the root
encoder's output for that slot, but after a retreat, an evolution or a Knock Out the slot holds
something else. Action tokens can still attend to earlier action tokens, so the model can learn to
track this. The consistency head measures how well it does.

## Data

The current rollout files (env/runner.js `packRollout`) record only the learner's own decisions:
its observation, action, log-probability and value per step, keyed `traj = game * 2 + seat`. They
hold neither the opponent's actions nor chance outcomes. A **sequence logger** is needed. For each
game it writes, from each player's view, the ordered actions of both sides and the outcomes that
player saw. It must leak no hidden information: a view contains only what that player could see,
otherwise the planner learns to cheat. It can run inside the existing runner on PPO self-play and
league games, with no new games.

Self-discovery rule: training games use random and built decks only, against the agent's own
league, never against SimpleBot or another hand-written bot. The archived lists and the bots are
for evaluation only, so the arch-A..D fine-tunes (log #49), which trained on archived lists against
SimpleBot, are not a starting point.

## Generality: what has to change to carry over to other TCGs

The goal is a general TCG method, not a Pokémon-specific one. The search above is game-agnostic,
but the current representation is not:

- **State tokens** have fixed Pokémon slots (Active and Bench 0–4 per side, env/tokens.js). A
  general version would encode entities: each card, with its zone, owner, attachments and counters,
  as one token, with zones as learned embeddings rather than fixed positions.
- **Action tokens** use Pokémon verbs and slot indices `[verb, card, slot1, slot2, name, extra]`. A
  general version would encode an action as a verb from the engine's own action types plus
  pointers to the entity tokens it targets, so the same model can read an MTG action.
- **Card features** combine hand-picked Pokémon fields (HP, retreat cost, attack costs;
  `card_feature_matrix`) with a frozen embedding of the rules text. The text embedding is general;
  the hand-picked fields are not, and should become optional.
- **Reward:** training pays 0 for a deck-out win (`--deckout-win 0`, logs #32–33). That is
  game-specific shaping: a human judgment that those wins are cheap. The general method should use
  only the game's own result.

These are out of scope for steps 1–2 below, but each new piece should take its inputs from the
engine's generic interface (zones, entities, legal-action objects), so the Pokémon-specific parts
can be swapped out later.

## Search

- **Gumbel MCTS** (Danihelka et al., 2022): sample m = 4–8 root actions without replacement (Gumbel
  top-k), then sequential halving with 16–32 simulations. It improves the policy even with few
  simulations, and few simulations limit how far the search can exploit the value's errors.
- **Chance nodes** after stochastic actions sample outcome tokens from the chance head.
- **Opponent nodes** use the model's policy for the opponent's side (the opponent's hidden hand is
  implicit in the model's belief, not dealt).
- **Compute.** A node is a prefix, so siblings share a KV cache and each expansion is one new token.
  Leaves are batched across concurrent games, as the GPU inference server does now. The load cap
  applies (0.8 memory fraction, ≤ 80% utilization, ≤ 16 threads).

## Steps and gates

1. **Sequence logger + offline model.** Train the prefix-LM on logged games. Gates, on held-out
   games: policy agreement and value calibration k = 1..8 steps ahead, against re-encoding the true
   state at step k; legality accuracy; chance-head log-loss.
2. **Hybrid search.** Gumbel MCTS on the model, with the engine supplying legal sets inside the
   current turn. Gate: at equal wall-clock, match psearch (log #50) against SimpleBot and head to
   head.
3. **Expert iteration.** Visit counts become the policy target, and values come from real
   outcomes. Gate: the greedy network improves on SimpleBot and on log #36's Energy-bias test (deck
   choice should move results by more than log #42's 2 points).
4. **Engine-free search.** Drop the engine's legal sets in favor of the legality head. Gate: no
   loss from step 3. This is the version that transfers to MTG.

## Risks

- **The search exploits the model.** This is the same mechanism as the builder exploiting the value
  (log #36). Mitigations: value targets from real results only, few simulations, and checking steps
  2–4 against psearch, which uses the real engine.
- **Error compounds with depth.** The gates measure it per k. Keep the tree shallow until they pass.
- **Cost.** A forward pass over a few hundred root tokens plus up to ~64 sequence tokens is cheap
  with a KV cache. Training adds the unrolled losses: roughly 2× the current per-batch cost,
  estimated, not measured.
