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

### #12 · 2026-10-05 · A2 · Baseline ladder: random, first-option, heuristic, SimpleBot
- **Done:** `HeuristicAgent` (set up, then attack with the strongest attack). The enumerator now
  drops Powers whose use opens a prompt the player can only cancel (Ditto's Transform with every
  copied attack blocked): the heuristic looped on them to the 5,000-step cap. Results saved in
  `notes/data/eval/ladder_*.json`.
- **Evidence:** 400 games per pair, all 24 decks, seat- and deck-swapped (win rate of the first
  agent): first-option vs random 79.0% ± 4.0; heuristic vs random 87.3% ± 3.3; heuristic vs
  first-option 86.8% ± 3.3; SimpleBot vs random 99.8% ± 0.5; SimpleBot vs first-option
  96.8% ± 1.7; SimpleBot vs heuristic 61.4% ± 4.8. The ladder is transitive. Dead-end rule
  verified against the oracle on 800 games (0 mismatches; 3,721 dead-end Powers dropped).
- **Found:** The Ditto loop would also have hit training: any policy can cycle use-Power ->
  cancel. Passing every turn beats random 79%: random play burns its own deck.
- **Next:** search rung, SimpleBot matrix, A3 training.

### #13 · 2026-10-05 · A2 · Search rung (flat Monte Carlo with determinization), not yet useful
- **Done:** `Game.clone(rng, viewer)` re-deals what the viewer can't see (own deck and prizes;
  the opponent's hand, deck and prizes) for search. `SearchAgent` tries each main-phase option
  in R determinized copies played on by the heuristic, to a turn horizon or the end of the game.
  `env/tools/matrix.js` (matchup matrix) and `rl/nash.py` (meta-game equilibrium by LP; uniform
  on rock-paper-scissors, pure on a dominant deck) are in for the SimpleBot baseline.
- **Evidence:** search vs heuristic: 4 rollouts, 2-turn horizon 25.0% ± 21.2 (16 games); 4
  rollouts to the end of the game 37.5% ± 16.8 (32 games, 154 s).
- **Found:** With few rollouts the search is noise around the heuristic and plays worse than
  it; the 2-turn score doesn't value setup. It needs many more rollouts (cost grows fast) to be a
  meaningful scale, so it is parked; SimpleBot is the top fixed rung for now.
- **Next:** A3 training is running (Wigglytuff vs Haymaker, league, evaluated every 20
  iterations against SimpleBot and the heuristic).

### #14 · 2026-10-05 · A3 · First run found no-op cycles; environment fixed
- **Done:** First A3 run (Wigglytuff vs Haymaker, both directions, self-play + snapshot league,
  14 workers) stopped at iteration 75. Environment fixes: (1) a cancel that only undoes the
  action that opened the prompt is no longer offered (checked by replaying the action and the
  cancel from a snapshot and comparing whole states); (2) any action whose prompt offers only
  cancel (the earlier Ditto rule, now for Trainers, retreat, Powers, Stadium, Trainers in play)
  is not offered; the oracle classifies both the same way. Fork `0a723c8`: deepClone copies onto
  the source's prototype instead of making the source the copy's prototype.
- **Evidence:** Run 1 against SimpleBot (200 games, greedy, both deck directions): it 19 31.0%;
  it 39 60.8% ± 6.8; it 59 68.2% ± 6.5 (73.5% / 63.0% by direction); against the heuristic
  65-66%. Then episodes grew from 189 to 713 decisions by it 74, 42% of them `cancel` (start
  Transform / a retreat / Super Energy Removal, cancel, repeat). After the fix, of 2,714 prompts
  offering cancel in 100 random games, 2,627 were pure undo. 400-game verification with the new
  rules: 0 mismatches. deepClone change: 300-game full-state traces identical, equivalence
  60/60, specs 250 + 686; throughput 48.2 -> 68.7 random-policy games/s/core.
- **Found:** With reward only at the end and no discount, nothing stops self-play drifting into
  free no-op cycles; they have to be removed from the action space. V8 slows objects that serve
  as prototypes, so `Object.create(source)` in every clone was a hidden engine-wide cost.
- **Next:** Restart A3 from scratch. (10,000-game verification of the new rules: 991,580 main-phase
  decisions and 383,794 prompts checked, 0 mismatches, 0 missing, 0 invalid, 0 engine errors.)

### #15 · 2026-10-05 · A4.2 · Token encoder, pointer model and GPU inference (infrastructure)
- **Done:** `env/tools/card_features.js` (277-card table: structured features and plain-text
  descriptions) and `rl/card_text.py` (all-MiniLM-L6-v2 embeddings of the descriptions, frozen).
  `env/tokens.js`: the state as card tokens (global, 12 slots, attached cards, hand, discards,
  unseen, opponent decklist, Stadium, prompt cards, picks) and each option as a candidate
  [verb, card, slot1, slot2, name, extra]. `rl/token_model.py`: TokenPointerNet (card embedding =
  features + text + learned residual; 3-layer transformer; candidates cross-attend to tokens and
  are scored by a pointer head; ONNX-exportable). Central GPU inference: `env/framing.js`,
  `env/remote_worker.js`, `rl/remote.py`; `rl/train.py` takes `--inference gpu` and
  `--model tokens`, and holds league snapshots as GPU model slots.
- **Evidence:** 200 random games: 74 tokens per state on average, 115 at most, at most 29
  candidates (padded to 128 / 48, no overflow). Text-embedding neighbours: Gust of Wind ->
  Switch; Energy Removal -> Super Energy Removal; Wigglytuff -> Jigglypuff. ONNX token inference
  on one CPU thread: 1.3-5.7 ms per decision (vs 0.06 ms for the MLP) — too slow; GPU inference
  through the workers: ~1,900 token-model transitions/s per worker (2,200 for the MLP) with the
  CPU busy training. 2-iteration token-model training run with a league slot and an ONNX
  evaluation works end to end.
- **Found:** A transformer per decision is ~30x the MLP's compute; on CPU it would dominate the
  environment by 20x, so the token model needs central batched inference.
- **Next:** A3 exit evaluation (run b) and the held-out run c; then A4.1 and the A4.2 comparison.

### #16 · 2026-10-05 · A3 · Exit met: beats SimpleBot in both directions, replicated
- **Done:** Run b (seed 1, ONNX rollouts, 160 iterations) and an independent held-out run c
  (seed 2, GPU inference, 140 iterations), both PPO self-play with a snapshot league on
  Wigglytuff (15+ #2 Lieu) vs Haymaker (15+ #1 Marshall), both deck directions. Exit evaluation
  with `rl/crossplay.py`; results in `notes/data/eval/a3_exit_*.json`.
- **Evidence:** Run b final, greedy: vs SimpleBot 97.9% ± 1.0 (n=800; 97.5% on Wigglytuff,
  98.2% on Haymaker); sampled 95.2% ± 2.1; vs heuristic 94.9% ± 1.5. Run c final vs SimpleBot
  97.2% ± 1.6 (98.0% / 96.5%). Held-out cross-play (200 games each): run b beats run 1's
  checkpoints 87-99.5% and run c's iterations 19-99 55-99.5%, but loses to run c's iterations
  119 and 139 (42.5%, 40.0%); run c final beats run b final 57.8% ± 4.8.
- **Found:** Beating SimpleBot is reproducible across independent runs, but the stronger of the
  two runs (more data per iteration) is not beaten by the other: run c is the A3 policy of
  record. The self-play passing phase (51% passes at iteration ~20) is transient.
- **Next:** SimpleBot 24 x 24 matrix (A2), then A4.1 on all 24 decks.

### #17 · 2026-10-05 · A2 · SimpleBot 24 x 24 matrix and its equilibrium
- **Done:** `env/tools/matrix.js --agent simplebot --games 100` over the 24 archived lists
  (276 pairs, mirrors 0.5), solved with `rl/nash.py`. Saved as
  `notes/data/eval/matrix_simplebot.json` and `nash_simplebot.json`.
- **Evidence:** 27,600 games in 284 s, 0 errors, 17 draws or cut off. Equilibrium: Sponge (10-
  #2 Bartlett) 0.469, Wigglytuff (11-14 #7 Pratt) 0.406, Articuno/Hitmonchan/Scyther (10- #8
  Diamond) 0.125. Best uniform-field win rates: Pratt Wigglytuff 0.737, Diamond 0.737.
- **Found:** Under SimpleBot piloting, Wigglytuff is in the support and Haymaker is not (best
  Haymaker list -0.17 against the equilibrium); this is the A5.1 reference for how the meta moves
  as play improves. SimpleBot matches are now fast (the engine speedups apply to its clones).
- **Next:** A4.1 training.

### #18 · 2026-10-05 · A4.1 · One MLP policy for all 24 decks: exit met at iteration 249
- **Done:** `runs/a4`: IdentityMLP (1024 x 3, 5.2M parameters), PPO self-play with a snapshot
  league over all 576 ordered deck pairs (16 workers x 4,096 transitions, GPU inference, seed 1).
  Stopped at iteration 249 of 400 (3 h 18 min). Exit evaluation with `runs/a4_exit.sh` (mirror
  and field steps): `notes/data/eval/a4_mirror_simplebot.json`, `a4_field_simplebot.json`.
- **Evidence:** In-training vs SimpleBot (400 games): it 24 29.4%, 49 53.6%, 99 81.1%, 149 84.4%,
  199 85.3%, 224 89.4%, 249 89.1% ± 3.0. Exit, 2,400 games, 100 per deck, greedy: mirror 89.25%
  ± 1.2 (lowest Viray Rain Dance 67%, Bartlett Sponge 77%; highest 97-98%); field 88.0% ± 1.3
  (lowest Viray 61%, Bartlett 75%, Morris Electabuzz 78%). Every deck above 50%. 0 errors; 44 /
  52 games cut off (scored as half).
- **Found:** Gains slowed to ~1 point per 25 iterations after iteration 100; it is ~9 points
  below the one-matchup A3 policy, with the losses concentrated in the 10-and-under lists. The
  trained-policy matrix and its Nash (the third step of `a4_exit.sh`) were not run.
- **Next:** A4.2: the token model on the same task, compared with this checkpoint.

### #19 · 2026-10-05 · A4.2 · Token-model training made affordable; mixed-model matches
- **Done:** `rl/train.py`: `--micro-batch` (each PPO minibatch accumulated over chunks; same
  gradient) and `--amp` (bfloat16 forward). For the token model each minibatch is sorted by
  token count and each micro-batch cut to its longest state. `rl/token_model.py`: attention
  through `F.scaled_dot_product_attention`, plain matmuls kept for the ONNX export.
  `env/agents.js`: `OnnxAgent` `reencode` mode (identity policy in a token-encoded game: encodes
  the state itself, maps the options to its ids, answers with the option index);
  `env/env.js` `visibleDecks()`; `env/tools/evaluate.js` uses it, so an MLP can play a token
  model. Check: `env/tools/check_reencode.js`.
- **Evidence:** Token model on all 576 pairs at minibatch 4,096: the whole-batch update filled
  the 16 GB GPU and spilled to shared memory (3 iterations not done in 10 min). Micro-batch
  1,024 fp32: 44 s train / iteration; + bf16, micro 2,048: 32 s; + length sorting and fused
  attention: 17 s (fp32 at micro 2,048 with these: 81-112 s). Micro-batched vs whole update on
  a test batch: parameters within 4e-8, identical stats. Fused vs matmul attention on 2,000 real
  states: logits within 2e-8; trimmed to the batch's longest state: identical (states 45-95
  tokens, mean 62, padding always at the end). Re-encoding: 7,959 decisions with 0 mismatches
  against the plain agent, 7,170 decisions in token games with 0 invalid; A4.1 vs an untrained
  token model 80/80.
- **Next:** Train the token model (`runs/a4-tok`, A4.1 settings, 250 iterations), then compare.

### #20 · 2026-10-05 · A4.2 · Two endless loops found by the token run; fixed, A4.1 re-scored
- **Done:** The first token run (`runs/a4-tok`, stopped at iteration 24) never finished its
  first SimpleBot evaluation; replaying each of the 16 worker chunks and then single games found
  two loops. (1) Clefable mirror: Metronome copies the other Clefable's Metronome, which prompts
  again; each copy nests another prompt (moves slowed from 6 to 80 ms), so the 5,000-step cap
  would take hours. Fork `3d2a13e`: Metronome can't copy Metronome (blocked in the copy prompt;
  nothing happens if it is the only attack), with 3 new specs. (2) Free start-then-undo cycles
  the #14 rule missed: Ditto's Transform whose copy prompt is left with only cancel after the
  replay check, and Rain Dance answered with "done" and nothing attached. `env/game.js`: any
  zero-pick answer (cancel or an empty done) that replays to the state before the action is
  dropped; if it is the only answer, the action is recorded as a dead end and not offered again
  in that state. Token run restarted from scratch on the fixed environment.
- **Evidence:** Clefable specs fail 3/3 without the fix; all 689 set specs pass (`nyc` itself
  exits non-zero). Game 93 (Clefable mirror) ends in 185 steps, game 103 (Transform cycle) in
  185, a Rain Dance mirror that cycled 1,500 steps in 104; the 16 evaluation chunks finish in
  11-14 s. Checks: 24/24 decks, 23/23 rulings, 68/68 card tests, engine equivalence 20/20,
  `test_env` PASS, `verify_enumerator` 400 games PASS, re-encoding 8,744 decisions 0 mismatches.
  A4.1 re-scored on the same seeds (`notes/data/eval/a4fix_*`): mirror 89.6% ± 1.2 (was 89.25%),
  field 88.5% ± 1.3 (was 88.0%), 0 games cut off (was 44 / 52, all Viray Rain Dance); Viray
  71% / 72% (was 67% / 61%), still the lowest deck.
- **Found:** Every cut-off game in the A4.1 exit was this Rain Dance cycle, so its weakest-deck
  score was partly an environment fault. A4.1 itself trained with both loops possible.
- **Next:** Token run on the fixed environment, then compare against the re-scored A4.1.

### #21 · 2026-10-05 · B1 · Phase B target set to Worlds 2011 (San Diego); coverage measured
- **Done:** Phase B target changed from 2013–14 to Worlds 2011, San Diego (HGSS-on: HGSS,
  Unleashed, Undaunted, Triumphant, Call of Legends, Black & White), by the user's choice for its
  smaller pool and simpler rules. `notes/scripts/ryuu_coverage_2011.py` parses the 2011 season's
  archetype lists from ptcgarchive (page saved in `notes/data/2011-season-ptcgarchive/decks.html`) and
  checks each card against the fork by name and printed set; results in
  `notes/data/eval/coverage_2011.json`. README: format table, B1 rewritten.
- **Evidence:** 13 lists, 153 distinct cards: 44 names have no implementation; by printing,
  0 lists are fully buildable. Missing copies per list: Zekrom/Pachirisu/Shaymin 0,
  Reshiram/Typhlosion 1 (Sage's Training), Magnezone/Emboar (Cohen, Worlds 1st) 8 (Magnezone
  Prime x3, Rayquaza & Deoxys LEGEND x2, Fisherman, Rescue Energy x2), Vileplume/Reuniclus (Cawthon,
  2nd) 14, Magnezone/Yanmega 18. The engine's HGSS folder has 23 cards.
- **Found:** By coverage alone 2011 is further from buildable than 2013–14 (57 of 60 for two
  Blastoise/Keldeo lists): most same-name Pokémon in the engine are other printings, and the
  printing match is partial (card images whose names didn't parse count as unknown printing).
  Archive lists are one per archetype, not the full Worlds top cut.
- **Next:** Source the Worlds 2011 top-cut lists; per-card text check of the same-name
  printings; then B2 (implement the HGSS-era gap) after the Phase A gate.

### #22 · 2026-10-05 · B1 · 2005 vs 2011 measured by printing: 2005 is no harder, and needs no new mechanics
- **Done:** `notes/scripts/ryuu_coverage_season.py` (replaces `ryuu_coverage_2011.py`) resolves
  every card of a season's ptcgarchive archetype lists to its printing (pokemon-tcg-data ids,
  cached in `notes/data/cache/tcgdata/`) and classes it against the fork: exact (same name and
  printed set), reprint (another set, identical card data), near-reprint (same structure, text
  at least 90% alike; to check by hand), different (same name, different card), missing.
  Engine cards are indexed by `name` and printed set, so cards without a `fullName` count (the
  #21 script missed them). 2005 page saved in `notes/data/2005-season-ptcgarchive/`. Results:
  `notes/data/eval/coverage_2005.json`, `coverage_2011.json`.
- **Evidence:** 2005 (19 lists, 1,140 copies, 139 names): exact 362, near-reprint 65,
  different 128, missing 516, unresolved 69; best list Birds 40/60. 2011 (13 lists, 780 copies,
  111 names): exact 224, reprint 110, different 267, missing 178, unresolved 1; best lists
  Reshiram/Typhlosion 42/60, Zekrom/Pachirisu/Shaymin 40/60. No list in either year is fully
  buildable. Mechanics: the engine has the Pokemon-ex rule (38 cards in its three EX sets) but
  no Lost Zone and no LEGEND cards, which 2011 needs (Lost World, Mew Prime's Lost Zone,
  Rayquaza & Deoxys LEGEND in the Worlds-winning list).
- **Found:** The decklist gap is about the same share in both years (names not buildable: 2005
  about 100 of 139, 2011 about 79 of 111), and the full legal pools are both about 600 cards
  short (2005: six EX sets missing, three complete; 2011: about 35 cards of six sets present).
  2005's missing cards sit inside mechanics the engine already plays; 2011 also needs new
  engine mechanics. The "different" class over-counts: some are wording-only changes (Double
  Colorless Energy), but most checked are real (HGSS Pokemon Communication and Rare Candy).
  #21's claim that 2011 was chosen for simpler rules does not hold against 2005.
- **Next:** Decide the Phase B target with these numbers (the README currently says 2011).
