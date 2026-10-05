# Pokémon TCG metagame RL

A reinforcement-learning project on the Pokémon Trading Card Game. The environment is
[evcoats/ryuu-play](https://github.com/evcoats/ryuu-play) (branch `sts-2000-pool`), a fork of
[keeshii/ryuu-play](https://github.com/keeshii/ryuu-play), the open-source Pokémon TCG simulator
in TypeScript. The fork is included here as the `ryuu-play/` submodule.

**The goal:** give an agent only a card pool and the rules. It learns to play any deck, learns
to build the decks worth playing, and then is checked against a real historical tournament
metagame that it never saw.

The end target is a full **World Championships metagame**. The first target is deliberately
much smaller: the **July 2000 Super Trainer Showdown (California)**. It has a 56-card field
that is now fully implemented in the engine and verified. Every part of the system gets built
and proven there first.

## Status

<!-- status:start -->
*Updated 2026-10-05.*

**Where things stand.** Phase A, milestone A0 is done: the engine runs the whole 2000 field and
is verified. The work now is A1, making the engine RL-ready, and its first step (committing two
measured throughput fixes) hasn't started. No agent has been trained yet.

**Earlier work:**

- **Log #1 (A0, engine covers the field).** All 24 archived STS lists build and play on the
  fork, with 541 engine specs, 68/68 interaction tests and 22/23 rulings passing (T18 open,
  outside this field). The engine runs ~9 games/s per core with no detectable first-player bias.

**Recent (log #2):** Set up the progress log and this recursive status. The two A1 throughput
fixes are still measured in a scratch test only (540 → 98 µs/action), not committed.

The full record is in [`notes/progress-log.md`](notes/progress-log.md).

**Next:**

1. A1.1: commit the throughput fixes (log cloning, `propagateEffect` card-order cache).
2. A1.2: legal-action enumerator, verified against the engine.
3. A1.3: observation encoder.
4. A1.4: seeded `reset` / `step` environment API.
5. A1.5: decide the training bridge (Node + ONNX rollouts vs. Python calling Node).
<!-- status:end -->

---

## The problem: three decisions stacked

| Level | Decision | Horizon | Learned by | Signal |
|---|---|---|---|---|
| **Move** | Which card, which target, which search pick | One prompt | Policy network over the legal candidates | Policy gradient and value from the game level |
| **Game** | How to pilot a fixed 60-card deck under hidden information | ~135 actions per game in this format | Self-play against a population of opponents | Win or loss |
| **Metagame** | Which deck to bring, given what everyone else brings | One tournament field | A deck-edit policy inside a PSRO loop | The matchup table produced by the game level |

Card metagames are non-transitive (rock–paper–scissors on top of raw power), so the target at
the top level is an **equilibrium mixture of decks, not one best deck**. The three levels are
coupled: play skill decides which decks look good, and the decks in the field decide which
play skills matter.

**Ground truth.** Archived tournament results are the answer key. An agent that starts from the
card pool and lands on the archetypes humans actually played has shown something that win rates
against its own checkpoints cannot. Human metagames are not equilibria, so the robust
comparison is **archetype rediscovery** (does the archetype appear in the agent's equilibrium
support, measured by card overlap with archived lists). Matching meta *shares* is not the goal.

---

## Why start in 2000

| | July 2000 STS (Base–Rocket) | A Worlds format (e.g. 2013–14) |
|---|---|---|
| Card pool in ryuu-play | **Complete**: every card in the field is implemented and verified | Mostly present, with real gaps (all of Team Plasma, Black Kyurem-EX, …) |
| Distinct cards in the field | **56** (21 Pokémon, 26 Trainer, 9 Energy) | Hundreds |
| Evolution | Three stacks in the whole field, max depth 2 | Deep lines, Rare Candy, many evolution engines |
| One player's full observation | **482 bits ≈ 60 bytes**; ~760–870 floats one-hot | Needs the scalable token representation |
| Recorded field | 24 top-8 lists across three age divisions | Large fields with placements |
| Mechanics | No abilities-era complexity, no EX/GX prize rules, no ACE SPEC | All of these |

The 2000 format is small enough to iterate on in hours on one machine and real enough to have
an answer key. Its weakness is also clear: there is **one** recorded field, and it is
concentrated (Wigglytuff 10/24, Haymaker 7/24, 8 archetypes). It can answer "does the agent find
Wigglytuff and Haymaker?" well. It cannot validate a predicted distribution. That is why it is
the proving ground and not the end result.

**The rule for Phase A:** anything that must scale to Worlds (the token representation, the
deck-general policy, the PSRO loop, the evaluation protocol) gets proven on 2000 first, against
a simpler baseline it must match or beat.

---

## Plan

### Phase A — Proving ground: July 2000 STS California

#### A0. Engine covers the field — ✅ done

On the engine fork, branch `sts-2000-pool`:

- Fossil Ditto re-enabled, and its two open TODOs closed (copying passive Pokémon Powers, and
  offering copied in-play Powers). Mr. Mime's Invisible Wall and Muk's Toxic Gas now work
  through Ditto.
- A new Wizards Black Star Promos set with the two promos the field played: Mewtwo #3 and Mew #8.
- **Verification:**
  - All 24 archived decklists build and start a game.
  - 541 engine specs pass (25 new).
  - 68/68 targeted card-interaction tests pass.
  - 1,926 card-data field checks against pokemon-tcg-data, with 1 cosmetic mismatch.
  - 22/23 dated 2000-era rulings pass. The failure (T18, Mysterious Fossil as a starting Basic)
    doesn't affect this field.
- **Measured:**
  - The engine runs ~9 real games/s per core and scales near-linearly to 8 workers.
  - No first-player bias is detectable (seat A won 54.5% ± 5.8 over 288 mirror games).
  - SimpleBot, the bundled bot, costs ~30× the engine per move (0.6 games/s/core), so it is an
    evaluation floor, not a self-play opponent.

#### A1. Make the engine an RL environment

The engine was built for a websocket server, not for millions of headless games. It has no
legal-move enumerator: an illegal action throws, and the store restores a deep-cloned backup.

1. **Throughput fixes.**
   - Stop deep-cloning `state.logs` on every dispatch. It grows all game long, which makes a
     game O(n²) in its length.
   - Cache the card order in `propagateEffect`, with a real invalidation rule.
   - Together these measured **540 → 98 µs/action (5.4×)** in a scratch test with all tests
     passing. They are not committed yet.
2. **Legal-action enumerator.** At every decision, list the candidate actions: play card,
   attach, evolve, retreat, use Power, attack, pass, and the options of every open prompt.
   Verify it against the engine: every enumerated action must be accepted, and a sampled
   non-enumerated action must be rejected.
3. **Observation encoder** following the measured layout (12 slots × 55 floats plus hand,
   discards, counts). Hidden information stays hidden: the opponent's hand shows as a size, and
   prizes are unknown to both players.
4. **Environment API**: `reset(deckA, deckB, seed) → obs, mask` and `step(action)`. Seeded, so
   games replay exactly. Each worker process runs many games.
5. **Training bridge.** *Decision:* run rollouts in Node with ONNX inference and train in
   PyTorch, syncing weights each iteration (recommended, since the networks are small and CPU
   inference is cheap), or call the Node engine from Python in batches.
6. **Housekeeping.**
   - Fix T18.
   - Run the spec, interaction, rulings and decklist checks as CI.

**Exit:** a seeded, enumerated, encoded environment at ≥ 50 random-policy games/s/core, with
the enumerator verified on every action across ≥ 10k games.

#### A2. Baselines and the evaluation ladder

- **Opponents:** random, a cheap heuristic bot, SimpleBot (floor), and a fixed-budget search
  bot as a relative scale.
- **Protocol:** every comparison is seat-swapped, with fixed decklists and confidence intervals.
  At 200 games the standard error is ~3.5 points.
- **Puzzles:** positions in this format with provable answers, such as lethal this turn,
  avoiding deck-out, and the right Energy Removal target.
- **Skill-ceiling baseline:** the full 24 × 24 matchup matrix and its Nash equilibrium **under
  SimpleBot**. This is the reference for how the discovered meta shifts as play improves.

#### A3. Game level, one matchup

PPO with a small self-play league, on the field's top two archetypes (Wigglytuff vs Haymaker),
using the identity-indexed encoding from A1.

**Exit:** beats SimpleBot by a clear, seat-swapped margin in both directions of the matchup, and
the result holds against held-out league checkpoints, not only its training opponents.

#### A4. Game level, every deck

1. **One deck-general policy**, conditioned on its own decklist and the opponent's, trained
   across all 24 archived lists.
2. **The scalable representation**, built here and required to match A4.1 before Phase B: card
   tokens, a verb head plus a pointer head over the legal candidates, and card embeddings built
   from card features and rules text.

**Exit:** beats SimpleBot with every deck; the trained-policy matchup matrix is stable across
reruns; and its matchup directions agree with era write-ups wherever those exist.

#### A5. Metagame level

1. **Fixed population.** Nash over the trained-policy matrix of the 24 archived lists. Do
   Wigglytuff and Haymaker sit in the support? Compare against the SimpleBot equilibrium from A2.
2. **Deck builder.**
   - A deck-edit policy (10–20 remove-and-add edits under construction rules) inside PSRO.
   - Diversity: a rectified-Nash meta-solver, exploiter episodes, and a MAP-Elites archive over
     deck descriptors.
   - New decks get piloting time before their matchup row is trusted.
3. **Two pool sizes.** Develop on the 56 cards the field played, which leaks human card choice
   but is cheap. Make the actual claim on the **full legal Base–Rocket pool**, which needs the
   remaining legal promos implemented. Most of those ~233 cards are unexercised by tests, so a
   cold-start builder will find engine bugs and treat them as strategies; expand verification
   first.

**Exit:** from a cold start on the full pool, archived archetypes appear in the equilibrium
support (by card overlap), and the result replicates across seeds. The three age divisions
serve as rough replicates of the human field.

#### A6. Play knowledge feeds deck building

- Use the play network's turn-zero value, averaged over opening hands, as the builder's edit
  reward, and compare it against a standalone matchup model.
- Reuse the play encoder's card-interaction weights to score candidate cards.

**Phase A exit gate**, all required before starting Worlds work in earnest:

- The token-pointer policy matches the identity-indexed one.
- Cold-start rediscovery succeeds on the full pool.
- The evaluation protocol and environment run unattended.

---

### Phase B — Full Worlds metagame

Phase B reuses everything from Phase A. What is new is the card pool, the scale, and the data.

#### B1. Choose the target Worlds by measurement, not preference

- **Coverage:** the candidates are the 2013 and 2014 formats.
  - The engine already holds much of the 2010–15 pool: 70 of 88 era staples are present, seven
    era archetypes are buildable, and two archived Worlds Blastoise/Keldeo lists build 57 of 60
    cards.
  - Missing: all of Team Plasma, Black Kyurem-EX, and others.
  - Earlier Worlds formats (2004–05) are mostly absent: 3 of 9 sets for 2005.
- **Data:** decklists and placements from Limitless and pokemon.com.
- **Legality:** build per-year legal pools from set codes. The current pool mixes sets that never
  coexisted, and an agent would invent decks no one could have played.

#### B2. Close the card gap with the Phase A verification pipeline

For every new card: card-data checks against pokemon-tcg-data, dated rulings tests, targeted
interaction tests, and every archived Worlds list as a regression deck.

#### B3. Scale

- The token representation carries over unchanged.
- Re-profile the engine on the larger pool and rerun the throughput budget before sizing PSRO.
  At 200 games per pair, one new row in a 40-deck population costs ~8,000 games.

#### B4. Game level, then metagame level on the Worlds pool

Same exit criteria as A4 and A5, measured against the archived Worlds top cut.

#### B5. Human evaluation

- Run the agent on a ryuu-play server against players who know the era (TCG ONE's Legacy format
  covers this pool).
- Use fixed archived lists, seat-swapped, ~200 games per opponent pool.
- The defensible claim is "beats experienced players on fixed lists within this pool."

---

## Risks

- **Play skill and the meta are coupled.** A weak pilot undervalues setup decks. Which
  archetypes appear as play improves is tracked as a result in its own right.
- **Engine bugs become meta bugs.** Archived lists double as regression decks, and the builder
  is only let loose on cards with test coverage.
- **One field in 2000.** The STS gives a single 24-deck field (STS New Jersey is a Gym-era format
  needing two unimplemented sets, 0/24 buildable). Phase A success means yes/no rediscovery,
  not distribution matching.
- **Human metas are not equilibria.** Rediscovery is the comparison; share percentages are not.
- **Worlds coverage.** "From scratch" claims in Phase B hold only for the buildable pool until
  B2 closes the gaps.

---

## Repository

| Path | Contents |
|---|---|
| `ryuu-play/` | Submodule: the engine fork, pinned to a commit on `sts-2000-pool`. Engine changes are committed there and the pin is bumped here. |
| `notes/progress-log.md` | Append-only log of finished todos, from which the Status section is summarized |
| `notes/tcg-rl-research-notes.md` | The research log and RL design, including the comparison with [Pokemon_TCG_RL](https://github.com/SuryaSGit/Pokemon_TCG_RL) (v4) |
| `notes/three-level-rl-pitch.md` | The three-level (move / game / metagame) pitch |
| `notes/sts-2000-engine-check.md` | The 2000 verification report: coverage, throughput, profiling, state vector |
| `notes/data/` | The archived STS decklists (scraped from ptcgarchive.com), aggregated to CSV and JSON |
| `notes/scripts/` | Harness, verification and measurement scripts (Node for the engine, Python for scraping and card-data checks) |

`notes/data/cache/` (raw scraped pages and the pokemon-tcg-data download) is not committed;
`meta_aggregate.py` and `ryuu_card_data_check.py` rebuild it on first run. The three
`*_v4.py` / `dims_v5.py` probes expect a local Pokemon_TCG_RL checkout at a hard-coded path.

### Setup

Requires Node.js 18.19+ (developed on Node 24).

```
git clone --recurse-submodules https://github.com/evcoats/ptcg-metagame-rl
cd ptcg-metagame-rl/ryuu-play
npm install --workspace=packages/common --workspace=packages/sets --workspace=packages/simple-bot
npm run compile -w packages/common && npm run compile -w packages/sets
(cd packages/sets && npx jasmine-ts "tests/**/*.spec.ts")      # 541 engine specs
cd ..
node notes/scripts/ryuu_sts_decks_check.js        # 24/24 archived decks build and start
node notes/scripts/ryuu_rulings_tests.js          # 22/23 (T18 open)
```

The scripts find the engine at `ryuu-play/` by default; pass a path or set `RYUU_PLAY` to
point them elsewhere.

## Credits

The engine and the ~900 card implementations are by keeshii and the ryuu-play contributors
(MIT). Card data was checked against
[PokemonTCG/pokemon-tcg-data](https://github.com/PokemonTCG/pokemon-tcg-data). Tournament data
is from [ptcgarchive.com](https://ptcgarchive.com/).
