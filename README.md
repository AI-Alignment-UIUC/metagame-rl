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

**Where things stand.** A0, A1 and A3 are done; A2 has its ladder and the SimpleBot matchup
matrix. A PPO self-play policy beats SimpleBot 97-98% in one matchup, and one MLP policy for all
24 decks (A4.1) beats it 88.5-89.6% with every deck above 70%. The token + pointer model (A4.2)
trains at 17 s per update, plays the MLP directly, and is retraining after its first run exposed
two endless loops, now fixed. Phase B targets Worlds 2005 (San Diego): its card gap matches
2011's, about 600 cards to the full legal pool, and it needs no new engine mechanics.

**Earlier work:**

- **Log #1 (A0, engine covers the field).** All 24 archived STS lists build and play on the
  fork, with 541 engine specs, 68/68 interaction tests and 22/23 rulings passing (T18 open,
  outside this field). The engine runs ~9 games/s per core with no detectable first-player bias.
- **Log #2–9 (A1.1–A1.6, plus the promos).** The environment was built and verified: the
  enumerator against an oracle on 10,000 games (0 mismatches over 1.65M checked decisions), the
  engine's speedups against the original store, all 2000 rulings (T18 fixed) and CI. Building it
  turned up engine faults — a Ditto Transform crash (fixed), prompt answers the engine never
  validates, and actions it accepts on the opponent's side — that the environment now guards
  against. All Base-era promos are in for the A5 full pool.
- **Log #10–16 (A1.6–A3).** The environment reached 68.7 random-policy games/s/core after a
  clone fix, and the A2 ladder is transitive (random < first-option < heuristic < SimpleBot);
  the first A3 run drifted into free start-then-cancel cycles, now removed from the action
  space. Two independent A3 reruns beat SimpleBot 97.9% ± 1.0 and 97.2% ± 1.6 in both deck
  directions, and the stronger (run c) beats the other 57.8%. The token model, central GPU
  inference and the A5 pieces (matchup model, edit builder, PSRO loop) are built and tested.

**Recent (log #17–22):** Under SimpleBot piloting the 24 x 24 matrix's equilibrium has no Haymaker
list in its support, and A4.1 met its per-deck exit (re-scored on the fixed environment: mirror
89.6%, field 88.5%, lowest Viray Rain Dance 71-72%, gains down to ~1 point per 25 iterations).
Token-model training was made to fit and run fast, mixed MLP-vs-token games work, and the two
loops the token run hit (Metronome copying Metronome; start-then-undo cycles, behind every game
A4.1's exit had cut off) are fixed. Measured by printing, Worlds 2005 and 2011 need about the same
share of their archived cards implemented (~72% and ~71% of names), but 2011 also needs the Lost
Zone and LEGEND cards, so Phase B moved from 2011 to 2005.

The full record is in [`notes/progress-log.md`](notes/progress-log.md).

**Next:**

1. A4.2: the token-model run on the fixed environment (`runs/a4-tok`, 250 iterations, A4.1 settings).
2. Supervised architecture check: token model vs MLP on 398k teacher-labelled states
   (`rl/distill.py`), plus ONNX / permutation / padding checks.
3. Compare the two RL policies: learning curves, mirror/field vs SimpleBot, head-to-head, cost.
4. A4 exit: the trained-policy matrix, its stability across reruns, and era write-ups.
5. A5.1: Nash over the trained-policy matrix; then PSRO with the builder.
6. B1: source the Worlds 2005 top-cut lists; verify the engine's three EX sets against card data
   and rulings; check the near-reprints by hand.
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

| | July 2000 STS (Base–Rocket) | Worlds 2005, San Diego (EX Ruby & Sapphire–EX Emerald) |
|---|---|---|
| Card pool in ryuu-play | **Complete**: every card in the field is implemented and verified | Partial: 3 of the 9 EX sets are in the engine (not yet verified); about 100 of the 139 card names in the season's archetype lists still need an implementation (see B1) |
| Distinct cards in the field | **56** (21 Pokémon, 26 Trainer, 9 Energy) | 139 card names across 19 archetype lists; nine EX sets plus POP Series 1 and promos in the format |
| Evolution | Three stacks in the whole field, max depth 2 | Deep lines, Rare Candy, many evolution engines |
| One player's full observation | **482 bits ≈ 60 bytes**; ~760–870 floats one-hot | Needs the scalable token representation |
| Recorded field | 24 top-8 lists across three age divisions | One archived list per archetype so far (ptcgarchive) and the four official 2005 World Championship decks; full top-cut lists not yet sourced |
| Mechanics | No abilities-era complexity, no EX/GX prize rules, no ACE SPEC | Poké-Powers and Poké-Bodies, Pokémon-ex (two Prizes), Dark Pokémon; all already in the engine. No ACE SPEC, no Lost Zone, no LEGENDs |

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

#### A1. Make the engine an RL environment — ✅ done

The engine was built for a websocket server, not for millions of headless games. It has no
legal-move enumerator: an illegal action throws, and the store restores a deep-cloned backup.

1. **Throughput fixes — ✅ done** (fork `888b385`).
   - Stop deep-cloning `state.logs` on every dispatch. It grew all game long, which made a game
     O(n²) in its length.
   - Cache the card order in `propagateEffect`, rebuilding it when a new card appears.
   - Measured **554 → 160 µs/action (3.5×), 18.7 → 64.6 engine-only games/s/core**, with the
     state identical to the old engine after every action over 300 seeded games
     (`notes/scripts/ryuu_engine_equivalence.js`).
2. **Legal-action enumerator — ✅ done** (`env/legal.js`). At every decision, list the candidate
   actions: play card, attach, evolve, retreat, use Power, attack, pass, and the options of
   every open prompt. Verify it against the engine: every enumerated action must be accepted,
   and a sampled non-enumerated action must be rejected. Verified against an exhaustive oracle
   (`env/oracle.js`) on every decision of 10,000 games: 0 mismatches.
3. **Observation encoder — ✅ done** (`env/encode.js`): 1,110 byte-exact features (12 slots ×
   54 plus hand, discards, unseen cards, counts) and 1,915 action ids. Hidden information stays
   hidden: the opponent's hand shows as a size, and prizes are unknown to both players.
4. **Environment API — ✅ done** (`env/env.js`): `reset(deckA, deckB, seed) → obs, legal` and
   `step(action)`. Seeded, so games replay exactly. Each worker process runs many games
   (`env/runner.js`).
5. **Training bridge — ✅ done.** *Decision:* rollouts in Node with ONNX inference
   (`env/rollout_worker.js`), training in PyTorch (`rl/train.py`), syncing weights each
   iteration.
6. **Housekeeping — ✅ done.**
   - Fix T18 (fork `fc4c8ec`, `Rules.fossilsAsStarters`).
   - Run the spec, interaction, rulings and decklist checks as CI (`.github/workflows/ci.yml`),
     plus the engine equivalence, env and enumerator checks.

**Exit:** a seeded, enumerated, encoded environment at ≥ 50 random-policy games/s/core, with
the enumerator verified on every action across ≥ 10k games. *Met: 0 mismatches over 10,000
games; 53.9 random-policy games/s/core (`env/tools/bench_env.js`).*

#### A2. Baselines and the evaluation ladder

- **Opponents:** random, a cheap heuristic bot, SimpleBot (floor), and a fixed-budget search
  bot as a relative scale.
- **Protocol:** every comparison is seat-swapped, with fixed decklists and confidence intervals.
  At 200 games the standard error is ~3.5 points.
- **Puzzles:** positions in this format with provable answers, such as lethal this turn,
  avoiding deck-out, and the right Energy Removal target.
- **Skill-ceiling baseline:** the full 24 × 24 matchup matrix and its Nash equilibrium **under
  SimpleBot**. This is the reference for how the discovered meta shifts as play improves.

#### A3. Game level, one matchup — ✅ done

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
   but is cheap. Make the actual claim on the **full legal Base–Rocket pool** (all legal promos
   are now in: Wizards Black Star Promos #1–#16, fork `64330a4`). Most of those ~233 cards are
   unexercised by tests, so a cold-start builder will find engine bugs and treat them as
   strategies; expand verification first.

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

#### B1. Target: Worlds 2005, San Diego

The 2005 World Championships (San Diego, August 19–21, 2005) were played in the Modified format:
EX Ruby & Sapphire, Sandstorm, Dragon, Team Magma vs Team Aqua, Hidden Legends, FireRed &
LeafGreen, Team Rocket Returns, Deoxys and Emerald, plus POP Series 1, the EX Trainer Kits and
Nintendo Black Star Promos 1–27. Wizards' four 2005 World Championship decks reproduce top
players' lists: Queendom (Jeremy Maron), Dark Tyranitar (Takashi Yoneda, a finalist), King of the
West (Michael Gonzalez) and Bright Aura (Curran Hill).

Chosen by measurement over Worlds 2011 (San Diego) and 2013–14. The card gap is about the same as
2011's, and 2005 needs no new engine mechanics.

- **Coverage, measured** (`notes/scripts/ryuu_coverage_season.py`, results in
  `notes/data/eval/coverage_2005.json` and `coverage_2011.json`; every card resolved to its
  printing through pokemon-tcg-data):

  | | 2005 | 2011 |
  |---|---|---|
  | Archetype lists (ptcgarchive) | 19 lists, 139 names | 13 lists, 111 names |
  | Names still to implement | ~100 (72%) | ~79 (71%) |
  | Copies buildable today | 362 of 1,140, +65 near-reprints to check | 334 of 780 |
  | Closest list | Zapdos/Moltres "Birds" 40/60 | Reshiram/Typhlosion 42/60 |
  | Full legal pool | 3 of 9 EX sets present, ~600 cards to go | ~35 cards of 6 sets present, ~600 to go |
  | New engine mechanics | none | Lost Zone, LEGEND cards |

  No list in either season is fully buildable yet. The most-played missing 2005 cards are
  Supporters and Trainers from the missing sets (TV Reporter, Steven's Advice, Rocket's Admin.,
  Swoop! Teleporter), Jirachi (Deoxys) and the Team Rocket Returns Dark Pokémon. "Different"
  (same name, different card) slightly over-counts, since a few are wording-only changes.
- **The engine's EX sets:** Ruby & Sapphire, Sandstorm and FireRed & LeafGreen are
  near-complete (about 109, 98 and 112 cards) but not yet checked against card data and
  rulings as the 2000 pool was.
- **2013–14, for comparison:** two archived Worlds Blastoise/Keldeo lists build 57 of 60 cards,
  but all of Team Plasma and Black Kyurem-EX are missing (`notes/tcg-rl-research-notes.md`).
- **Data:** the season's archetype lists (ptcgarchive, saved in
  `notes/data/2005-season-ptcgarchive/`) and the World Championship decks. Full Worlds 2005
  top-cut lists and placements are still to be sourced.
- **Legality:** build the 2005 legal pool from set codes. The current pool mixes sets that never
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
| `env/` | The RL environment: seeded game loop, legal-action enumerator and its oracle, encoder, env API, rollout runner and workers; `env/tools/` has the verification, test, benchmark and evaluation scripts |
| `rl/` | The learner: PyTorch models, ONNX export, rollout reader, PPO training (`python -m rl.train`) |
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
git clone --recurse-submodules https://github.com/AI-Alignment-UIUC/ptcg-metagame-rl
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

The environment and training (from the repository root):

```
npm install                                        # onnxruntime-node for the rollout workers
node env/tools/test_env.js                         # env API and encoder
node env/tools/verify_enumerator.js --games 200    # enumerator vs. the oracle
node env/tools/bench_env.js                        # random-policy games/s on one core
node env/tools/evaluate.js --x simplebot --y random --games 200
py -3 -m venv .venv && .venv/Scripts/pip install torch numpy onnx   # (CUDA build of torch from download.pytorch.org)
.venv/Scripts/python -m rl.train --run runs/try --matchup "Wigglytuff|Haymaker" --both-directions
```

## Credits

The engine and the ~900 card implementations are by keeshii and the ryuu-play contributors
(MIT). Card data was checked against
[PokemonTCG/pokemon-tcg-data](https://github.com/PokemonTCG/pokemon-tcg-data). Tournament data
is from [ptcgarchive.com](https://ptcgarchive.com/).
