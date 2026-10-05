# Progress log

Append-only. One entry per finished todo, newest at the bottom. Entries are never edited or
deleted afterwards; a correction is a new entry that says what it corrects. The README status is
summarized from this log (see `CLAUDE.md`).

Entry format:

```
### #N · YYYY-MM-DD · <plan item, e.g. A1.2> · <todo in a few words>
- **Done:** what changed, with paths, commits or the submodule pin.
- **Evidence:** tests run and their results, numbers measured, or "not verified".
- **Found:** anything learned along the way: bugs, surprises, open questions. Omit if nothing.
- **Next:** what this makes possible or points to next.
```

---

### #1 · 2026-10-04 · A0 · Engine covers the 2000 STS field (backfilled)
- **Done:** On the fork's `sts-2000-pool` branch: Fossil Ditto re-enabled with its two open TODOs
  closed (copying passive Pokémon Powers, offering copied in-play Powers), and a new Wizards
  Black Star Promos set with Mewtwo #3 and Mew #8. Report in `notes/sts-2000-engine-check.md`.
- **Evidence:** 24/24 archived lists build and start a game; 541 engine specs pass (25 new);
  68/68 interaction tests; 1,926 card-data checks with 1 cosmetic mismatch; 22/23 rulings.
  ~9 games/s per core, near-linear to 8 workers; seat A won 54.5% ± 5.8 over 288 mirror games.
- **Found:** Rulings test T18 (Mysterious Fossil as a starting Basic) fails; not in this field.
  SimpleBot costs ~30× the engine per move, so it's an evaluation floor only. Two throughput
  fixes (log cloning, `propagateEffect` card-order cache) measured 540 → 98 µs/action in a
  scratch test but are not committed.
- **Next:** A1, starting with committing the throughput fixes.

### #2 · 2026-10-05 · Housekeeping · Progress log and recursive status
- **Done:** Added this log, a `## Status` section in `README.md`, and the update rules in
  `CLAUDE.md`, following Wu et al. 2021 (recursive summarization).
- **Evidence:** Not applicable (documentation only).
- **Next:** A1.1.

### #3 · 2026-10-05 · A1.1 · Commit the throughput fixes
- **Done:** Fork commit `888b385`: `Store.reduce` keeps existing log entries by reference instead
  of deep-cloning them into the rollback backup; `propagateEffect` replaces the per-effect sort
  with precomputed ranks (rebuilt when an unseen card appears) and bucketing. New
  `packages/common/src/store/store.spec.ts` (7 specs). Folded in `notes/scripts/ryuu_engine_equivalence.js`
  (differential test, old vs new Store) and fixed its illegal-retreat generator, which used bench
  slot 4 (a real slot), so 18 "illegal" retreats were legal and accepted by both engines.
- **Evidence:** common 250/250 specs, sets 684/684. Equivalence, 300 seeded SimpleBot games:
  state identical after every one of 41,381 actions, 3,651,418 card-order checks equal; after
  the generator fix, 40 games at 30% injection rejected 3,922/3,922 illegal actions with no
  value change. `ryuu_selfplay.js --nopolicy --games 300 --seeded`, same machine:
  554 → 160 µs/action, 18.7 → 64.6 games/s/core (3.5×).
- **Found:** The scratch estimate (98 µs, 5.4×) was optimistic; it skipped the logs entirely and
  keyed the cache on array length. Rejected illegal actions still change which arrays are
  shared (deepClone doesn't preserve sharing), identically in old and new engines; values are
  unaffected. Where the remaining 160 µs/action goes is not profiled yet.
- **Next:** A1.2 legal-action enumerator. The A1 exit target (≥ 50 games/s/core) is met by the
  engine alone, so the enumerator and encoder have ~25% headroom; profile again after them.

### #4 · 2026-10-05 · A5.3 prep · Fold in the Black Star Promos
- **Done:** Fork commit `64330a4`: 12 promo cards (Pikachu #1/#4, Electabuzz #2, Dragonite #5,
  Arcanine #6, Jigglypuff #7, Meowth #10, Eevee #11, Mewtwo #12, Venusaur #13, Cool Porygon #15,
  Computer Error #16) with specs, registered in `init.js`; #9 and #14 are reprints. Folded in
  the matching script changes: promo set in the rulings and throughput scripts, card-number
  matching in `ryuu_card_data_check.py`, `--flag` handling in `ryuu_harness.js`, and the new
  `ryuu_promo_fuzz.js`.
- **Evidence:** 143 new specs pass (in the 684). Card-data check: 2,025 field checks, 12 matched
  by card number, 1 known cosmetic mismatch (Raticate Super Fang). `ryuu_promo_fuzz.js --games
  400`: 400/400 finished, 0 stuck, 0 cap, 0 errors; every promo attack, Power and Trainer used.
- **Found:** Mew's Devolution Beam came up only 2 times and Texture Magic 4 times in 400 games;
  they rely on specs more than play.
- **Next:** Back to A1.2.

### #5 · 2026-10-05 · A1.2 · Legal-action enumerator, verified against an oracle
- **Done:** `env/legal.js`: main-phase options (attach, basic, evolve, trainer, retreat, attack,
  Power, Stadium, Trainer-in-play, pass) with canonical keys (copies of a card are one option,
  empty Bench slots one target), and prompt answers built one pick at a time in canonical order,
  checked with the prompt's own decode + validate. `env/oracle.js` tries every action shape on
  a clone; `env/tools/verify_enumerator.js` compares the two on every decision. `env/game.js`
  is the seeded game loop (coin flips, shuffles and face-down prize picks answered from the
  game's RNG). Fork `253399e`: Ditto's Transform now blocks copied attacks it can't pay for.
- **Evidence:** 10,000 random-policy games, every decision checked: 1,120,594 main-phase
  decisions with 0 mismatches; 527,852 prompts against 10.7M legal raw answers, 0 missing,
  0 invalid; 0 engine errors, all games finished. Ditto specs 12/12.
- **Found:** The engine's Store never decodes or validates prompt answers (only the websocket
  server does), so the env does it. The engine accepts rules-illegal actions: Energy onto the
  opponent's Pokemon, Basics onto their Bench, evolving their Pokemon, using their Pokemon
  Power (all excluded by the enumerator, counted as leniency). Legality sometimes lives behind
  a coin flip (a Smokescreen-style effect flips before the Energy check), so trials run with
  all heads and all tails. A copied attack's legality is decided after its prompt resolves, so
  copy prompts are checked by replaying the chain from a snapshot.
- **Next:** encoder, env API, bridge.

### #6 · 2026-10-05 · A1.3 · Observation encoder and action indexing
- **Done:** `env/encode.js`: 1,110 features from the decider's view (12 slots x 54, per-player
  sizes and flags, card-count vectors for my hand, both discards, my unseen cards and the
  opponent's decklist, turn, Stadium, open prompt and picks so far); every feature a multiple
  of 1/48, so observations travel as bytes exactly. 1,915 action ids cover every option key.
- **Evidence:** `env/tools/test_env.js`, 300 games / 61,785 decisions: all features byte-exact
  (largest 228), every offered option has an id, ids distinct per decision.
- **Next:** env API.

### #7 · 2026-10-05 · A1.4 · Environment API
- **Done:** `env/env.js`: `reset(deckA, deckB, seed)` and `step(actionId)` returning the
  deciding player, observation and legal ids; both seats through the same calls.
- **Evidence:** seeded games replay exactly (test_env.js replays every 4th game: identical
  observation hashes and results).
- **Next:** training bridge.

### #8 · 2026-10-05 · A1.5 · Training bridge: Node rollouts + ONNX, PyTorch training
- **Done:** Decision taken as recommended. `env/runner.js` plays many games per process and
  batches each agent's decisions into one inference call; `env/agents.js` (ONNX policy,
  random, first-option, SimpleBot); `env/rollout_worker.js` (JSON-lines control, binary
  rollout files); `rl/model.py` (IdentityMLP 1.8M params, ONNX export), `rl/rollouts.py`,
  `rl/train.py` (PPO with GAE per player trajectory, masked softmax, optional snapshot
  league). `env/tools/evaluate.js`: seat- and deck-swapped matches with 95% CIs (A2 protocol).
  Root `package.json` (onnxruntime-node); Python deps in a git-ignored `.venv` (torch 2.11 +
  CUDA on the RTX 5070 Ti).
- **Evidence:** ONNX matches PyTorch to 5e-7; inference 55 us/decision at batch 64 on one
  thread. 3-iteration smoke run trains end to end (~1,300 transitions/s per worker).
  SimpleBot beats random 96.9% ± 3.5 (96 games); always-first-option beats random 75%.
- **Found:** Random play is weak enough that passing every turn beats it: random burns its own
  deck with draw Trainers.
- **Next:** A1.6, then A2/A3.

### #9 · 2026-10-05 · A1.6 · T18 fixed, CI
- **Done:** Fork `fc4c8ec`: `Rules.fossilsAsStarters` (default on, as upstream; off in our
  Base Sets format, env and harness). T18 now recognizes a mulligan; the rulings script exits
  non-zero on a failure. `.github/workflows/ci.yml` runs engine specs, decklists, rulings,
  card interactions, engine equivalence, env tests and a 200-game enumerator check.
- **Evidence:** rulings 23/23, decks 24/24, interactions 68/68, specs 250 + 686.
- **Next:** CI runs on the next push (A1 milestone).

### #10 · 2026-10-05 · A1 · Environment throughput
- **Done:** Env: no game log, resolved prompts dropped once none is open, no rollback backup
  (only enumerated actions are dispatched), trials share the card-order cache, stop at the end
  of the turn, and skip unaffordable attacks and retreats using the engine's own cost queries;
  card code gets a plain copy of the engine's exports (TypeScript's getter chains cost 15%).
  Fork `01bbe57`: deepClone with a Map (was O(n^2)), no-op cards skipped in effect
  propagation, counting sort for the card order.
- **Evidence:** `env/tools/bench_env.js`, random policy, one core: 4.5 -> 38.1 games/s
  (1,064 -> 127 us/step, 206 steps/game). Equivalence after the engine changes: 150/150
  games identical, 1.83M order checks equal. Enumerator re-verified on 2,000 games (0
  mismatches) after the optimizations, before the 10,000-game run in #5.
- **Found:** A1's exit target (>= 50 random-policy games/s/core) is not met yet: 38.1. Random
  play makes long games (206 decisions, vs ~135 actions with SimpleBot). Remaining time is the
  engine's effect propagation (~50%) and clones for trials (~17%).
- **Next:** more throughput (fewer trials for common Trainers, cheaper propagation), then A2.

### #11 · 2026-10-05 · A1 · Throughput target met; A1 closed
- **Done:** Trials skip the post-action state check (knockouts, prizes, winner), since the
  reducers settle legality. Fork `dfd7085`: the engine's knockout scan skips undamaged Pokemon
  (no card lowers HP). New `env/tools/trace_hash.js` fingerprints whole-state traces to check
  engine changes the equivalence test can't swap.
- **Evidence:** `bench_env.js`, random policy, one core: 38.1 -> 41.2 (trials) -> 53.9
  games/s (90 us/step). 300 seeded games: full-state traces identical with and without the
  knockout-scan change. Final code re-verified on 10,000 games: 1,120,394 main-phase
  decisions and 528,637 prompts (10.7M legal raw answers), 0 mismatches, 0 missing, 0 invalid,
  0 engine errors. Specs 250 + 686, rulings 23/23, decks 24/24, interactions 68/68.
- **Found:** Most of a turn change was the knockout scan: one HP-check propagation per Pokemon
  in play after every action. The submodule's `origin` is upstream; the fork is the remote
  `mine`.
- **Next:** A2 (heuristic rung, search rung, SimpleBot matrix, puzzles), A3 training.
