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

### #23 · 2026-10-05 · B1 · Phase B target set to Worlds 2005, San Diego
- **Done:** By the user's decision on #22's numbers, README Phase B now targets Worlds 2005 (San
  Diego, August 19–21, 2005; Modified: EX Ruby & Sapphire through EX Emerald, POP Series 1, EX
  Trainer Kits, Nintendo promos 1–27). Format table and B1 rewritten with the 2005 vs 2011
  coverage table from #22; 2013–14 kept for comparison. This supersedes #21's choice of 2011.
- **Evidence:** Numbers as measured in #22 (`notes/data/eval/coverage_2005.json`,
  `coverage_2011.json`). Event dates, legal sets and the four 2005 World Championship decks
  (Maron, Yoneda, Gonzalez, Hill) from pokumon.com; not cross-checked against a second source.
- **Next:** Source the Worlds 2005 top-cut lists; verify the engine's EX sets (card data,
  rulings) before B2 adds the six missing sets.

### #24 · 2026-10-05 · A5 · Three-tier answer key and counter table
- **Done:** `rl/answer_key.py` scores a deck population (an agent's meta: decks, matchup matrix,
  its Nash mixture) against the archived field in three tiers: staples (cards in at least 75% of
  archived lists; recall at weighted inclusion >= 0.5, counts within one copy of the field's
  median), archetypes (best card overlap of each archived archetype with an equilibrium-support
  deck, rediscovered at >= 0.5), and the counter table (each deck's best counter, its win rate =
  the deck's exploitability). README: ground-truth section rewritten around a meta drafted from
  random decks with the archive used only to score it; A5 gains item 4 (counter table,
  single-opponent counter-deck search, archived decks as held-out entries) and a three-tier exit.
- **Evidence:** Baseline on the SimpleBot 24 x 24 matrix (`notes/data/eval/answer_key_simplebot.json`),
  where the "agent" is SimpleBot's Nash over the human lists: 7 staples, 6 played (86%; Item
  Finder missing), counts within one for 83% (5 of 6); archetypes 6 of 8 at overlap >= 0.5
  (trivially 1.00 for the three in the support, since the population is the archive). The three
  hardest decks to exploit form a cycle and are the Nash support: Bartlett Sponge (best counter
  Manquez Wigglytuff 57%), Diamond Articuno/Hitmonchan/Scyther (Bartlett 63%), Pratt Wigglytuff
  (Diamond 65%); most other Wigglytuff and Haymaker lists have an 85-93% counter. 100 games per
  pair (about ±10 points per cell).
- **Found:** Field staples in the 2000 lists: Professor Oak 24/24, Double Colorless Energy, Gust of
  Wind and Computer Search 23/24, Scyther 20/24. A real score needs a cold-start population.
- **Next:** Score the trained-policy matrix (A4 exit) and, in A5, PSRO populations from random
  decks.

### #25 · 2026-10-05 · A4.2 · Supervised check of the token architecture
- **Done:** `env/tools/distill_data.js`: the A4.1 policy plays itself over all deck pairs (10%
  random moves) and every decision with more than one option is saved in both encodings with
  the teacher's greedy choice and the final result. `rl/distill.py` trains a token model (1.6M
  parameters, as in RL) and a fresh IdentityMLP (5.2M) on the same rows, scores them on held-out
  games, and checks the token model's ONNX export, candidate permutation and padding trim.
  Results: `notes/data/eval/a4_distill.json`. Dataset in `runs/distill/` (not committed, 1 GB).
- **Evidence:** 2,560 games, 397,663 decisions: 0 decisions with two options encoded alike, 0 token
  or candidate overflows (at most 118 tokens, 41 options). Train 345,596 rows (seeds 1-7), test
  52,067 (seed 8, other games); chance 21.5%. Token model held-out top-1 69.6% (main phase 67.8%,
  prompts 75.0%; 2 options 83.6%, 11+ options 58.4%), value MSE 0.664 at its best epoch (3), sign
  accuracy 71.3% at the end. MLP 78.3% (76.7 / 83.3%), value MSE 0.866 at its best epoch (1),
  sign accuracy 69.0%. After training: ONNX logits within 1.5e-5 of PyTorch, top choice 100%
  the same; shuffled candidates give the same logits shuffled (difference 0); trimmed padding
  identical. 12 epochs: token 4.4 min, MLP 48 s.
- **Found:** The token model learns the teacher well above chance and predicts the result better
  than the MLP; the policy gap is expected, since the MLP student reads the teacher's own
  encoding with 3x the parameters. The token model ends with training loss 0.72 against the
  MLP's 0.06 and plateaus at about 69.6%: it is short of capacity, not overfitting. Both value
  heads overfit within a few epochs (one result label per game).
- **Next:** The RL comparison (#26); a wider or deeper token model is the obvious next knob.

### #26 · 2026-10-05 · A4.2 · Token model matches and beats A4.1
- **Done:** `runs/a4-tok`: TokenPointerNet (width 192, 3 layers, 1.6M parameters) on the A4.1 task
  and settings (576 ordered pairs, 16 workers x 4,096 transitions, league snapshots every 25,
  seed 1, 250 iterations), on the fixed environment of #20. Resumed once at iteration 134 with
  micro-batch 1,024 and a 60% GPU memory cap (`rl/train.py --gpu-mem-fraction`; same updates)
  after the desktop lagged. Benchmark with `runs/a4_compare.sh` on A4.1's exit seeds (same
  deals), summary `notes/data/eval/a4_compare.json` / `.txt`.
- **Evidence:** In-training vs SimpleBot, token / A4.1: it 24 29.7 / 29.4%, 49 62.7 / 53.6, 99
  78.0 / 81.1, 149 90.0 / 84.4, 199 88.5 / 85.3, 249 92.6 / 89.1. Exit, 2,400 games, greedy:
  mirror 93.2% ± 1.0 (A4.1 89.6%), field 93.3% ± 1.0 (A4.1 88.5%); better on 16 / 21 of 24 decks,
  worse on 5 / 1 by at most 4 points; lowest deck 74% (Viray Rain Dance) / 78% (A4.1 71% / 72%).
  Head to head, token vs A4.1: mirror 67.8% ± 1.9, field 65.9% ± 1.9, above 50% on 24 of 24 decks
  in both (lowest 55-57%: Sponge, Electabuzz/Mr. Mime, Haymaker). Cost: 3 h 37 min wall (A4.1
  3 h 18 min); about 63 s per iteration at the end, of which ~45 s collecting games.
- **Found:** Game collection grew from 7 s to 45 s per iteration as league snapshots were added
  (each is its own GPU model, so inference batches split). Before the resume, GPU memory sat at
  14.3 of 16 GB and the update had slowed to 30-71 s: the run itself was spilling. A4.1 trained
  before #20's fixes, so it may have lost some training to the loops.
- **Next:** A4 exit: the trained-policy matrix with the token policy, a rerun for stability,
  era write-ups; score it with `rl/answer_key.py`.

### #27 · 2026-10-05 · A5 · Builder design: PSRO with a matchup model, explored by restarts and optimism
- **Done:** README A5.2 rewritten (the user's choice among three designs: real-game search only,
  a matchup model ranking candidates, or the play network's value alone). PSRO proposes card
  swaps ranked by a matchup model whose inputs are both decks (mean card embeddings from the
  token model) and the pilot's start-of-game value v(A, B) over ~16 openings; real games decide
  what enters the matrix. Exploration: random restarts with an edit budget drawn per search
  (8-60 cards), a 5-model ensemble ranked by mean + beta x spread, and a minimum distance of
  ~10 cards for a new population deck. Dropped from the plan unless plain search stalls: the
  RL-trained edit policy, MAP-Elites, rectified Nash, exploiter episodes. A6's first item is now
  the ablation of the value feature.
- **Evidence:** Plan only. Cost basis: with the token pilot, 2,400 games took 126-150 s on 16
  workers (about 16-19 games/s), so 100 games against each of 5 support decks is ~25-30 s per
  candidate; ranking with the model and confirming the top 5 is ~20x cheaper per step than
  testing 100 candidates with games.
- **Next:** Implement in `rl/matchup.py` (value feature, ensemble) and `rl/psro.py` (restarts,
  budgets, distance rule); develop on the 56-card field pool, then the full pool.

### #28 · 2026-10-05 · A5 · Metagame-builder schematic in the repo
- **Done:** `notes/schematics/metagame-builder.html`, a standalone page diagramming the A5 PSRO
  loop (population and real-game matrix, Nash, matchup model, swap search, confirmation,
  piloting) with each step marked built, partly built or planned, and the three-tier scoring.
  Linked from the README's Repository table.
- **Evidence:** Drawn from `rl/psro.py`, `rl/nash.py`, `rl/matchup.py`, `rl/builder.py`,
  `rl/decks.py`, README A5 and log #24/#27. Not rendered in a browser from the repo copy (the
  same page was viewed as a published artifact).
- **Found:** The code and the #27 plan differ at step 4: `rl/psro.py` still proposes decks with
  the PPO edit policy of `rl/builder.py`, which #27 drops for restarts with edit budgets; the
  distance rule is 0.1 (6 cards) against the planned ~10.
- **Next:** A first cold-start PSRO run on the field pool to see whether staples come back.

### #29 · 2026-10-05 · A5 · Schematic shown in the README
- **Done:** `notes/schematics/metagame-builder.svg`, the diagram of #28 as a standalone light-theme
  SVG (system font fallbacks), embedded at the top of README A5 with a caption linking the full
  page and noting that step 4 in the code is still the PPO edit policy.
- **Evidence:** The SVG parses as XML. Not checked on GitHub's renderer.
- **Next:** The cold-start run `runs/a5-cold1` (started 23:41) is in progress.

### #30 · 2026-10-06 · A5 · PSRO matrix games on the GPU: 14x faster, identical results
- **Done:** `rl/gpu_matrix.py` plays matchup-matrix games with central GPU inference: a new
  `games` command in `env/remote_worker.js` (slot-0 policy in both seats, results per game) and
  greedy serving in `rl/remote.py` (argmax when the request asks for it). Same jobs and seeds as
  `env/tools/matrix.js`. `rl/psro.py` uses it by default (`--inference gpu|cpu`), keeps the
  workers loaded across iterations, logs games/s and seconds per phase, and measures the last
  iteration's proposals before stopping (they were added but never played before).
  `env/tools/matrix.js` now also writes total decisions per pair (`steps`) and prints decisions
  per game. The first cold-start run (`runs/a5-cold1`, CPU) was stopped in iteration 0.
- **Evidence:** 16 random decks on the field pool, 32 games per pair (3,840 games), token pilot
  `runs/a4-tok/model_it00249.pt`, seed 8: CPU ONNX workers 366 s (10.5 games/s), GPU 26.8 s
  (143 games/s). All 120 pairs have identical wins and identical decision counts on both paths,
  so the same Nash mixture. GPU PSRO smoke run (6 decks, 2 iterations) completes, ~65-75 games/s
  at that small size.
- **Found:** Random decks make longer games than the archived lists: 211-213 decisions per game
  (per-pair median 213, 90th percentile 274, max 326) against about 135, with no pathological
  pair; that alone makes a cold-start matrix ~1.6x dearer per game. The CPU run's ~4-5 games/s in
  iteration 0 was below the 10.5 measured afterwards on the same decks; not explained.
- **Next:** The cold-start run `runs/a5-cold2` (16 random decks, 12 iterations, 100 games per
  pair) on the GPU path.

### #31 · 2026-10-06 · infra · Load cap at ~80% of the machine after three crashes
- **Done:** The machine crashed or hung three times on 2026-10-04 to 06: a hypervisor bugcheck
  (0x20001) at 00:53 on the 6th, during the card ablations of #32, and two hangs in sleep that
  needed the power button. `rl/limits.py` now caps every job: GPU memory at 80% of the card
  (`set_per_process_memory_fraction`, at most 0.8 even if a flag asks for more), at most 14 Node
  workers plus 2 torch threads (16 of 20 threads), and a watchdog that warns on stderr when the
  GPU sits at 95% or more for three 30 s polls or reaches 83 C. `rl.train`, `rl.psro`, `rl.distill`,
  `rl.crossplay` and `GpuMatrix` (so every script that builds one) apply it; default worker
  counts drop from 16-18 to 14. Rule in `CLAUDE.md` ("Machine load limits"). Commits 30faf32,
  77cc51d, and this one for `GpuMatrix`.
- **Evidence:** A 14 GB allocation is refused under the cap and 4 GB passes; `--workers 16` is
  cut to 14; one watchdog per process; the watchdog's `nvidia-smi` read works. Under the cap,
  GPU-matrix ablation games ran at 75-110 games/s (before: 63-83 at 16 workers), with GPU
  utilization 42% mean and 66% at most, 2.9 GB, 200 W at most, 53 C. `rl.tests`,
  `env/tools/test_env.js --games 100` and `verify_enumerator.js --games 200` pass.
- **Found:** Not thermal as far as the logs show: no WHEA or thermal events, and the GPU idles at
  36 C. GPU utilization can't be capped from PyTorch; a 240 W power limit (default 300 W) from an
  admin shell is the hard cap. #26's run had sat at 14.3 of 16 GB before its resume.
- **Next:** The deck-out diagnosis (#32).

### #32 · 2026-10-06 · A5 · Why staples don't come back: the pilot plays for deck-out
- **Done:** `runs/a5-cold2` (16 random decks, field pool, 12 iterations, 100 games per pair, GPU
  matrix) finished: population 64, final equilibrium a single deck, `psro11-1` (Wigglytuff-like,
  48% overlap with the nearest archived list). `notes/scripts/card_ablation.py` measures what a
  card is worth to a pilot: in every archived deck that plays it, all copies are replaced by the
  deck's main basic Energy, and the original plays the cut copy, seat-swapped, 200 games per
  deck. Results in `notes/data/eval/card_ablation_a4tok.json` (token pilot, GPU) and
  `card_ablation_simplebot.json` (SimpleBot, CPU). Game results now say how each won game ended
  (`Game.ending`: prizes, deck-out, no-pokemon, other; passed through `env/runner.js` and
  `env/remote_worker.js`, counted in `GpuMatrix.last["endings"]`).
- **Evidence:** Staples per deck, archived / random start / PSRO-added / final deck: Computer
  Search 2.71 / 1.00 / 0.12 / 0, Item Finder 2.12 / 1.19 / 0.12 / 0, Double Colorless Energy
  3.29 / 0 / 0.04 / 0, Professor Oak 3.38 / 1.50 / 1.15 / 4. Original's win rate over the cut
  deck, token pilot (± 95%): PlusPower 41.8 ± 1.6, Bill 45.8 ± 1.7, Item Finder 46.5, Computer
  Search 46.6, Gust of Wind 46.6, Lass 47.3, Super Energy Removal 47.3, Scoop Up 47.9 (all
  below 50); Energy Removal 52.0, Double Colorless Energy 55.9, Scyther 58.1, Professor Oak 68.2.
  SimpleBot: PlusPower 40.1 ± 2.2, Item Finder 43.2, Gust 43.7, Computer Search 44.5, Oak 48.9,
  DCE 51.7. Controls (token pilot, 100 games, Marshall's Haymaker): against an identical copy
  43% (noise, ± 10), against the deck with its Hitmonchan, Mewtwo and Scyther cut 81%; 0 games
  cut off. Bill's engine code draws 2, as printed. Endings, 2,208 token-pilot games over the
  archived field (8 per pair): deck-out 987 (45%), prizes 856 (39%), no Pokémon 365 (17%), 242
  decisions per game. 200 SimpleBot games: prizes 149 (75%), deck-out 28 (14%), no Pokémon 23
  (12%), 134 decisions per game.
- **Found:** The token pilot has learned a stalling game that ends by deck-out almost half the
  time, so any card that draws or searches speeds its own loss, and the cheapest filler, a basic
  Energy, beats Bill, Computer Search and Item Finder. PSRO under this pilot is therefore right
  to drop them: the staples didn't return because the pilot, not the builder, devalues them. Every
  A5 measurement made with this pilot (matrices, ablations, a5-cold2) carries that bias.
  SimpleBot misuses the same cards for other reasons (14% deck-outs), so it is no fix. Training
  rewards a win the same whether by prizes or deck-out, and nothing charges for game length.
- **Next:** Make the pilot play for prizes: first find whether deck-outs grow during training
  (`runs/a4-tok` checkpoints, short matrices), then try a short run with a per-turn cost or a
  smaller reward for deck-out wins, judged by the ending mix and SimpleBot win rate; rerun the
  ablations and a5-cold2 after.

### #33 · 2026-10-06 · A5 · Paying less for deck-out wins: fewer deck-outs, staples still undervalued
- **Done:** `rl/train.py --deckout-win R`: a win by deck-out earns R instead of 1 (losses stay
  -1), via `Runner(deckoutWin)` in `env/runner.js` and both rollout workers; the training log now
  counts endings per iteration. `rl/limits.py` gained `Pace`, used in the PPO update: after each
  optimizer step it rests a quarter of the step's time, holding the GPU to ~80% busy (#31's
  watchdog showed 86% mean during updates without it). Test (`runs/deckout_test.sh`): two
  15-iteration self-play fine-tunes of `runs/a4-tok/model_it00249.pt`, identical but for R = 0
  (`runs/deckout-w0`) and R = 1 (`runs/deckout-w1`, the control).
- **Evidence:** Deck-outs grow during the original training (greedy, 4 games per pair over the
  field): iteration 24 7%, 74 32%, 149 26%, 249 44%, as games lengthen from 103 to 246 decisions.
  Sampled self-play, first / mean of last 5 iterations: R = 0 deck-out 55.8 / 34.9%, prizes
  31.9 / 48.2%; control 61.0 / 55.6%, prizes 25.9 / 29.4%. Greedy, final checkpoints: R = 0
  deck-out 27%, prizes 56%; control 39% / 44%; it249 44% / 42%. Against SimpleBot (400 games):
  R = 0 93.0% ± 2.5, control 95.5% ± 2.0. Card ablation (100 games per deck), R = 0 / control:
  Bill 49.1 / 47.6, Computer Search 45.8 / 44.8, Item Finder 47.2 / 46.8, PlusPower 43.8 / 42.0,
  Professor Oak 67.8 / 66.0, DCE 57.3 / 56.6 (± 2.0-2.4); files
  `notes/data/eval/card_ablation_deckout_w{0,1}.json`. With Pace, GPU 46% mean, 53% max over a
  training update (172 W, 52 C); updates take 24-25 s instead of 20.
- **Found:** Corrects #32: deck-out is not the whole reason the pilot undervalues the staples.
  Cutting deck-outs by a third (control 39% to 27%) moved no card's value beyond noise, and
  PlusPower, which draws nothing, is the most negative card under every pilot. The pilot misuses
  these Trainers in other ways (when and on what it plays them), not shown yet. R = 0 is kept as
  the better pilot for A5, at no measurable cost in strength.
- **Next:** The three builder designs of #27 compared under the R = 0 pilot (games, matchup
  model, pilot value), each checked on a short run first; separately, a trace of how the pilot
  plays PlusPower and Computer Search.

### #34 · 2026-10-06 · A5.2 · The three builder designs compared: the pilot's value wins
- **Done:** `rl/search.py`: one restart search for PSRO with the three scorers of #27, chosen by
  `rl/psro.py --builder games|model|value --search-seconds S`. Restarts from a random deck or a
  support deck kicked 10 random swaps away, an edit budget of 12-60 cards per search, hill
  climbing by single-card swaps (half the added cards are ones the deck already plays), and new
  decks at least 10 cards from every deck. Scorers: games, real games against the top 6 support
  decks weighted by sigma (24 per pair, the same deals for every candidate of a step); model, a
  5-member ensemble of matchup models refit on resampled results, ranked by mean + 1.0 x spread
  (no value feature: that is A6's ablation); value, the pilot's start-of-game value against the
  support decks (8 openings). model and value search for 90% of the budget, then their top 8
  distinct finalists play real games against the support and the best are proposed (A5.2 step
  3). The log keeps each proposal's predicted score, the scorer's own estimate and its real win
  rate once measured. `notes/scripts/compare_builders.py` scores the runs on a shared panel.
  Fixes found by the smoke runs: the token encoder scores at most 48 options and built decks
  exceed that, which crashed GPU inference (index out of range) and would have made ONNX agents
  read the next row's logits, so `env/env.js` now offers only the first 48; `GpuMatrix` job seeds
  above 2^53 lost precision in Node and mixed up results, so seeds are bounded and asserted.
- **Evidence:** `runs/builders_compare.sh`: the same 16 random decks (seed 3), field pool, pilot
  `runs/deckout-w0/model_it00014.pt`, 8 iterations, 4 new decks each, 120 s of search per
  iteration, 48 games per pair. Wall time games 19.2 min, model 21.1, value 19.0. Candidates
  scored: games 1,404 (one to three searches per iteration, so 15 proposals, population 31),
  model 8.6 million, value 643,164 (32 proposals each, population 48). Error of each scorer's
  own estimate against the proposal's real win rate: games 0.081, model 0.587 (it predicted
  0.75-0.90 for decks that won 0-61%), value 0.268. Panel (`notes/data/eval/builders_compare.json`):
  each run's final support (games 5 decks, model 3, value 1) plus the 24 archived lists, 60
  games per pair, 31,680 games, 0 errors. Final mixtures, against the archived field: games
  37.9%, model 26.5%, value 50.3%. Head to head: value beats games 76.5% and model 74.3%; model
  beats games 59.1%. Best panel deck against each mixture: games 84.9% (Pratt's Wigglytuff),
  model 86.7% (same), value 71.7% (Marshall's Haymaker). Panel Nash: archived 0.875, games
  0.125, model and value 0. value's final deck overlaps Marshall's Haymaker 77% and plays 4 DCE,
  3 Computer Search, 3 Bill, 2 Oak, 3 Scyther, 4 Energy Removal, 3 Super Energy Removal, but no
  Item Finder, Gust of Wind or PlusPower.
- **Found:** The pilot's value is the best scorer here by every panel measure: it sees ~450x the
  candidates of real games, stays roughly calibrated, and its deck reaches parity with the human
  field while the others fall well short. Real-game scoring is the most honest (error 0.08) but
  affords one or two climbs per iteration, so it explores little. The matchup model is badly
  exploited: searching a million candidates against a model fitted on 16-48 decks finds the
  decks it overrates, and confirmation games only pick the least bad of a bad shortlist. Offline,
  the same model predicts held-out pairs well (MAE 0.06-0.07, 89-92% of directions, 64 decks
  of a5-cold2) but, trained on 16 decks, predicts new decks no better than 0.5 (MAE 0.25 vs
  0.26), so it fails exactly where the search takes it. One seed and 60 games per pair: not yet
  replicated. All three populations still lose to the human lists in the panel Nash.
- **Next:** Replicate with two more seeds; give the model a trust region (candidates within ~15
  cards of measured decks) or the value as a feature before ruling it out; then value-scored
  PSRO for longer, and on the full pool.

### #35 · 2026-10-06 · A5.2 · 2000s result #1 written up; #34's nearest list corrected
- **Done:** `results/2000s-result-1/`: the builder comparison of #34 as a standalone result, with
  its own README (question, setup, panel and search tables, the value-built deck beside the nearest
  archived list, limits, how to reproduce) and its data: the three runs' logs, populations and
  matrices, the panel results, the launch script, and the pilot checkpoint with the script that
  made it (7.5 MB). `results/README.md` indexes results by era. Linked from the README's
  Repository table.
- **Evidence:** Overlap of `value5-0` with every archived list: Chris Graham's Haymaker
  (10-and-under #6) 0.767, Ken Knight's Clefable 0.667, Daniel Nino's Haymaker 0.633, Alvin
  Osborn's Haymaker 0.600; Andrew Marshall's Haymaker (15+ #1) 0.450. Against Graham's list it
  has the same Hitmonchan / Electabuzz / Scyther / DCE / Energy Removal / Computer Search / Bill
  core and swaps PlusPower 3, Gust of Wind 2, Scoop Up 2, Ditto 2, Energy Retrieval 2 and one
  each of Oak, Scyther and Super Energy Removal for 12 Lightning Energy, a Hitmonchan and a Machop
  (34 Energy against 22).
- **Found:** Corrects #34: the nearest archived list to value's final deck is Graham's, not
  Marshall's. Marshall's is the best response to it in the panel (71.7%), which is where #34's
  wording went wrong. The swaps away from Graham's list are the Trainers the pilot undervalues
  (#32-33).
- **Next:** As #34: two more seeds, the model with a trust region or the value feature, then
  value-scored PSRO longer and on the full pool.

### #36 · 2026-10-06 · A5.2 · The value-built deck floods Energy because the value head misjudges it
- **Done:** `notes/scripts/trainer_restore_test.py`: four 60-card variants, from 2000s result #1's
  `value5-0` (11 Pokémon, 15 Trainers, 34 Energy) to Chris Graham's list (22 Energy), each
  scored by the pilot's start-of-game value against the 24 archived lists (16 deals each) and by
  real games (100 per pair, 10,200 games, 0 errors). Also counted the Trainers across the value
  run's population.
- **Evidence:** The search did explore the Trainers: the 16 random starting decks held PlusPower in
  14, Gust of Wind in 13, Item Finder in 10, but the 32 built decks hold Gust in 0, PlusPower in
  3, Item Finder in 2, and basic Energy rose from 17.4 to 30.4 per deck. Value-predicted / real
  win rate against the field (± 0.020): built 0.560 / 0.499; 6 Lightning swapped for PlusPower 3,
  Gust 2, Oak 1: 0.518 / 0.576; 12 Lightning swapped for Graham's Trainers: 0.477 / 0.632;
  Graham's list: 0.502 / 0.681. Head to head, Trainers restored beats the built deck 59-63%;
  Graham's list beats all three variants 59-62%.
- **Found:** The pilot plays these Trainers well enough to win more with them; its start-of-game
  value ranks the four decks almost in reverse of their real results. The search followed that
  value into an Energy flood: the deck stopped where the value head stopped, not because Trainers
  were unexplored. With #32-33 this fits diminishing returns the value head misses: one Energy
  for one Trainer in a 22-Energy deck can help, the 30th Energy does not. Result #1's ranking of
  the three designs stands, but its deck is capped by this error.
- **Next:** Confirm more of the value search's finalists with real games, or recalibrate the value
  head on varied decks (train on built and random decks, not only the 24 archived ones); check
  how far a value search with that fix gets toward Graham's 0.681.

### #37 · 2026-10-06 · A6 · What the matchup model should see: inputs help, the data is the limit
- **Done:** `notes/scripts/matchup_ablation.py`: five antisymmetric matchup models on every deck and
  result of 2000s result #1's three runs (merged): the pilot's value alone (calibrated, both seat
  orders, 16 deals), deck-shape features alone (counts of Energy, Pokémon, Basics, Trainers, draw
  cards, the share of basic Energy some attack needs, and a goldfish proxy: the chance a Basic can
  pay its cheapest attack by turn 2 / 3), value + shape, the card-embedding model of
  `rl/matchup.py`, and all of them. Scored on held-out decks (5 folds by deck), then trained on
  everything and asked to rank log #36's four Trainer variants against the 24 archived lists
  (never in the data). Results in `notes/data/eval/matchup_ablation.json`.
  `GpuMatrix.values` now sends at most 4,096 deals per forward pass: one pass of ~40k states
  ran into the 80% memory cap.
- **Evidence:** 95 decks, 2,481 pairs, 130,608 games. Held-out error / winner right / rank of the
  held-out decks (Spearman): value 0.236 / 57.0% / +0.27; shape 0.191 / 70.4% / +0.64; value +
  shape 0.189 / 69.8% / +0.65; embed 0.157 / 77.5% / +0.73; all 0.161 / 76.7% / +0.69. Ranking
  of the four variants against their real order (0.499 < 0.576 < 0.632 < 0.681): value -0.20,
  shape -1.00, value + shape -1.00, embed -0.40, all -0.80; the raw value (0.663, 0.625, 0.634,
  0.637) also puts the 34-Energy deck first. Learned shape weights: basic Energy +0.14,
  Trainers -0.14, Basic Pokémon +0.74, attack by turn 3 +0.25.
- **Found:** With ~100 decks of data, the card-embedding model now generalizes to new decks (log
  #34 found it no better than a coin from 16 decks), and the value adds nothing on top of it. But
  every model ranks the Trainer variants wrong, and the shape models exactly backwards, because
  the data teaches it: every deck in these runs is either a random deck (17 Energy, scattered
  Trainers) or an Energy-heavy built deck, so more Energy and fewer Trainers goes with winning.
  No deck in it is a coherent Trainer-heavy list, and no input can recover what the data never
  shows. The search's own bias shapes the data every model learns from.
- **Next:** Put the missing contrast in the data: real games for controlled variants (a good
  shell with N Energy vs Trainers, as in #36) and the archived lists, then refit; and in the
  search, explore the Energy / Trainer balance on purpose (swap blocks of Energy for Trainers)
  rather than only single cards.

### #38 · 2026-10-06 · A6 · A deck-strength model with five input groups: game statistics carry it
- **Done:** `notes/scripts/deck_strength.py`: no opponent context; predicts a deck's win rate
  against the 24 archived lists from five standardized input groups with a binomial logistic
  model: shape (counts, Energy fit), goldfish (attack by turn 2 / 3, Energy in the first 10),
  game statistics (turns and decisions per game, deck-out and no-Pokémon endings), value (the
  pilot's start-of-game value and its value at game turn 5 in play), uncertainty (cards changed
  from the nearest other deck). Decks: all of 2000s result #1's runs plus the archived lists
  (Graham's held out), 117 in all, each against the field at 40 games per pair; alternating pairs
  of games give the target, the rest the statistics and in-play value, so no input comes from
  the games it predicts. Held out: log #36's four Trainer variants. `env/runner.js` can record
  each seat's value at a given turn (`valueAtTurn`) and reports game turns; the remote worker
  returns them with each game's seed; `GpuMatrix.play` keeps per-game results (`.results`).
  Results in `notes/data/eval/deck_strength.json`.
- **Evidence:** 115,200 games at 150 games/s, 0 errors, 100 cut off; about 476 target games per
  deck; win-rate sd 0.171. Held-out (5 folds by deck) MAE / rank correlation: constant 0.146 /
  0; all groups 0.058 / +0.89; only game statistics 0.066 / +0.84; only value 0.119 / +0.53;
  only goldfish 0.128 / +0.43; only shape 0.133 / +0.41; only uncertainty 0.147 / -0.12. Without
  game statistics 0.087 / +0.75; without any one other group 0.053-0.058 / +0.89 to +0.91. Group
  |weight| per sd: game statistics 1.45, shape 0.67, value 0.62, goldfish 0.18, uncertainty
  0.12. Largest weights: decisions per game +0.95, value at turn 5 +0.43, Basic Pokémon -0.25,
  no-Pokémon endings +0.23, start-of-game value -0.19. Trainer variants, predicted / real:
  0.385 / 0.525, 0.421 / 0.582, 0.536 / 0.635, 0.590 / 0.700, so the order is right (rank +1.0)
  but the level is ~0.12 low; their decisions per game rise 209, 227, 253, 257 as Trainers come
  back, while the start-of-game value falls 0.325, 0.253, 0.262, 0.270.
- **Found:** How a deck plays carries almost all of the signal: game statistics alone nearly
  match everything, and dropping them is the only removal that hurts. Decisions per game is the
  strongest single input; it rises with Trainers, so it reads as "this deck has things to do".
  Given the rest, the start-of-game value gets a negative weight while the turn-5 value is
  positive: the opening judgment is the misleading part, as in #36. Shape, goldfish and
  uncertainty add nothing once game statistics are in, and uncertainty predicts nothing alone,
  as expected of a trust signal. With the archived lists in the data the Trainer variants are
  now ranked right (#37 had them backwards). Caveats: the statistics came from ~480 games per
  deck, which would already measure its win rate directly; correlated inputs (turns, decisions)
  make single weights unstable, so the group drops are the reliable reading; linear model.
- **Next:** How few games the statistics need (8, 16, 32 per deck) before they stop helping; if
  few suffice, a search that plays a handful of games per candidate and ranks by this model.

### #39 · 2026-10-06 · A5.2 · The deck-strength model as the search's scorer: accurate, too slow
- **Done:** `rl/strength.py`: the deck-strength features and model of #38 in one module, used by
  training and the search alike. `notes/scripts/deck_strength.py` now takes the game statistics
  from 8, 16 or 32 games per deck (other games than the target's), saves the 16-game model
  (`notes/data/eval/strength_model.json`) and per-deck data. `rl/search.py` `StrengthScorer`:
  each candidate plays 16 games against the top 4 support decks (game statistics, value at turn
  5), its start-of-game value against them (4 deals, both seat orders), its decklist features and
  its distance to the population, ranked by the model; climbs capped at 20 steps (~2 s a step).
  `rl/psro.py --builder strength`. `runs/strength_run.sh`: result #1's setup (seed 3, the same
  16 random decks, 8 iterations, 4 new decks, 120 s, 48 games per pair). The model's weights were
  fitted on data that includes the archived lists (no decklist enters the search).
- **Evidence:** Statistics from few games, held-out MAE / rank (constant 0.142): 8 games 0.071 /
  +0.81, 16 games 0.067 / +0.84, 32 games 0.066 / +0.85, all (~290) 0.055 / +0.90; at 16 games
  the four Trainer variants are not separated (rank 0.00; they differ by 5-18 points). Search:
  2 climbs per iteration, 1,740 candidates in all, population 35 (19 added); the first built deck
  entered the support at iteration 6; final support `strength7-0` (Wigglytuff-like, 0.64),
  random-15, random-8. Built decks kept 18-25 Energy and PlusPower / Gust; the closest to any
  Haymaker list is 0.50. Error of the scorer's estimate against real results 0.046. Panel
  (`notes/data/eval/builders_compare_strength.json`, the four runs' supports plus the 24 archived
  lists, 60 games per pair): against the field games 37.4%, model 25.9%, value 49.7%, strength
  30.7%; value's deck beats strength's mixture 90.2%; best panel deck against strength 90.2%.
- **Found:** The strength scorer is the best calibrated of the four (0.046) and avoids the Energy
  flood, but at ~2 s a candidate it explores as little as real-game scoring, and 120 s an
  iteration never gets a climb far from a random deck. Its accuracy cannot buy breadth, and with
  16 games it cannot tell close variants apart either. The value search finds good basins fast
  but misranks within them; the strength model ranks within them but cannot find them.
- **Next:** Two stages: the value search for breadth, then the strength model (with its 16 games)
  to choose among many finalists and among Energy / Trainer variants of each (block swaps), so
  the cheap scorer explores and the honest one decides; same setup, then the panel.

### #40 · 2026-10-06 · A5 · The loop closed: piloting every PSRO iteration
- **Done:** `rl/psro.py --pilot-iters N`: after each iteration's proposals, the pilot is
  fine-tuned N PPO iterations (`rl.train`, self-play, deck-out wins pay `--pilot-deckout-win`, 0
  by default) on the new decks against the top 6 support decks both ways, the support among
  itself and 8 random population pairs; the GPU matrix is reloaded with the new checkpoint (its
  workers are closed while training runs) and the whole matrix is re-measured under it. Rollout
  files are deleted after each step (~200 MB). `runs/iterated_run.sh`: result #1's value search
  (seed 3, 16 random decks, 8 iterations, 4 new decks, 120 s, 48 games per pair) with
  `--pilot-iters 5`; pilots in `runs/cmp-value-iter/pilot/itNN/`.
- **Evidence:** Piloting took 133-160 s per iteration; deck-outs in the last training iteration
  fell 0.40, 0.30, 0.22, 0.12 over the first four steps, then 0.12-0.22. Mean Energy of the
  proposals by iteration 22.5, 28.2, 31.2, 30.8, 29.2, 30.8, 31.8, 30.5; mean |value - real| of
  the proposals 0.191, 0.150, 0.175, 0.187, 0.137, 0.083, 0.145, 0.038. Final equilibrium one
  deck, `value5-1` (Articuno / Hitmonchan-like, 57% overlap): 32 Energy, 4 DCE, 4 Oak, no
  PlusPower, Gust or Computer Search. Panel (#41's, six runs' supports plus the 24 archived
  lists, 60 games per pair) under the original pilot: against the field 60.7%, best panel deck
  against it 70.0%, beats result #1's value deck 58.3%; under its own final pilot: field 71.9%,
  exploitability 53.3%, 0.30 of the panel's Nash (the first built decks with any).
- **Found:** Closing the loop made the strongest metagame so far, the first built mixture that
  beats the archived field (60.7% under the pilot all runs share), but not by fixing the Energy
  bias: the proposals stayed at ~30 Energy and the value's error fell only at the end. The pilot
  and the decks co-adapt: the same deck gains 11 points under the pilot trained on its games.
  Graham's list is still ahead (68.1% against the field under the original pilot, #36).
- **Next:** #41, the same loop with stochastic deck picking.

### #41 · 2026-10-06 · A5 · Stochastic deck picking in the closed loop: diverse, human-like, weaker
- **Done:** `rl/search.py --search-temperature T` (`rl/psro.py`): climb steps, finalists and
  proposals drawn from softmax(score / T) without replacement instead of the best (a climb keeps
  the best deck it visited); 0 is the greedy search. At T = 0.03 a 0.55 / 0.52 / 0.50 / 0.40
  choice goes 65 / 23 / 12 / 0.4%. `runs/iterated_t03_run.sh`: #40's run with T = 0.03.
  `notes/scripts/compare_builders.py` panels of all six runs (games, model, value, strength, the
  greedy loop, the stochastic loop) under three pilots: `notes/data/eval/loop_panel_{orig,greedyloop,stochloop}.json`.
- **Evidence:** Mean Energy of the proposals by iteration 19.2, 23.0, 20.0, 20.2, 25.8, 25.0,
  20.8, 24.0; mean |value - real| 0.106, 0.034, 0.142, 0.121, 0.039, 0.087, 0.034, 0.134. Final
  equilibrium five decks: Wigglytuff-like 0.36 (25 Energy), Rain Dance-like 0.35 (24 Energy,
  3 Gust, 3 Computer Search), random-15 0.16, Haymaker-like 0.08, Rain Dance-like 0.05; 19-25
  Energy, PlusPower in 3 of 5. Against the field (pilots: original / greedy loop's /
  stochastic loop's): games 37.4 / 38.0 / 39.0%, model 25.4 / 31.5 / 28.7%, value (result #1)
  50.6 / 56.8 / 53.7%, strength 29.9 / 33.9 / 33.9%, greedy loop 60.7 / 71.9 / 60.2%,
  stochastic loop 32.9 / 41.5 / 43.1%. The greedy loop's mixture beats the stochastic loop's
  72.5 / 75.8 / 59.4%. The archived lists keep the panel's whole Nash except under the greedy
  loop's pilot (0.70).
- **Found:** Sampling did what it was meant to: the proposals kept human-like Energy counts and
  Trainer packages, the value stayed better calibrated on average, and the equilibrium spread over
  four archetypes instead of one. But those decks are weaker in every panel; under these pilots
  the Energy-heavy deck is genuinely strong (#36 showed Trainers help a 34-Energy shell, not
  that fewer Energy wins in general). Both are single seeds, and search outcomes vary a lot by
  seed, so neither ranking is settled.
- **Next:** Two more seeds of both loops; a longer stochastic run (diverse populations may need
  more iterations to converge); score both against the answer key (staples, archetypes).

### #42 · 2026-10-06 · A4 / A5 · A pilot that never sees a human list
- **Done:** `notes/scripts/pilot_decks.py`: 512 random legal decks with no human deck shape (1-4
  Pokémon lines, Energy uniform 8-34, 75% of it of the Pokémon's types, Trainers at random; the
  card pool is still the field's 56 cards) and 2,048 random matchups. `runs/pilot_scratch_run.sh`:
  `runs/a4-tok`'s settings (token model, 1.6M parameters, league, 250 iterations) trained from
  scratch on those decks only, deck-out wins paying 0 from the start; evaluated against SimpleBot
  on the archived decks every 25 iterations (evaluation only). Diagnostics (`runs/pilot_diag.sh`):
  SimpleBot on 24 held-out random decks, head to head with result #1's pilot on the archived
  decks, log #36's Energy-bias test, and endings. Results in
  `notes/data/eval/pilot_scratch_{diag,h2h}.json`.
- **Evidence:** Against SimpleBot on the archived decks by iteration (scratch / original a4-tok):
  24 40.5 / 29.7%, 49 47.7 / 62.7, 74 54.5, 99 60.9 / 78.0, 124 62.0, 149 61.9 / 90.0, 174 76.5,
  199 76.2 / 88.5, 224 73.4, 249 78.7% ± 4.0 / 92.6. On held-out random decks against SimpleBot:
  scratch 67.3% ± 4.6, result #1's pilot 55.5% ± 4.9. Head to head on the archived decks, scratch
  wins 13.5% ± 3.3 against result #1's pilot. Endings on the archived field: deck-out 19%, prizes
  66%, no Pokémon 14% (result #1's pilot: 27 / 56 / 17%; a4-tok it249: 44 / 42 / 14%), 181
  decisions per game. Energy-bias test, value-predicted / real against the field (± 0.020): built
  34-Energy deck 0.607 / 0.623; 6 Lightning for Trainers 0.629 / 0.605; 12 Lightning for Graham's
  Trainers 0.605 / 0.620; Graham's list 0.635 / 0.613. Wall time ~4 h (collection grew from 7 s
  to 55 s an iteration as league snapshots were added, as in #26).
- **Found:** Without human lists the pilot learns slower on the archived decks and ends ~14 points
  below the human-trained pilot there, and loses to it badly on its home decks, but it generalizes
  better to unseen random decks (+12 points) and stalls far less. Its value head no longer
  overrates Energy: it rates Graham's list highest and its predictions are within 0.03 of real
  results. But under this pilot the four variants all score 0.61-0.62: deck choice barely changes
  its results (spread 2 points against 18 under result #1's pilot), so it would give the deck
  builder little signal. Unbiased but weak: deck differences only show with a strong pilot.
- **Next:** Make the human-free pilot stronger before using it for deck building (longer training,
  a larger model since #25 found underfitting, exploiters, self-imitation), then rerun the closed
  loop with it. See `notes/analysis-2026-10-06.md`.

### #43 · 2026-10-07 · A5 · The pilot's representations in the search: novelty finds a real deck, the edit head overfits the value faster
- **Done:** `rl/deck_head.py` (commits `4b2075a`, `2cae02b`, `7055b83`): `GpuMatrix.values(states=True)`
  returns the start-of-game states the value is read at and the encoder's token 0 (`TokenPointerNet.encode`
  split out of `forward`; `env/remote_worker.js` reports which deals produced a reading). From them,
  `--novelty λ`: score + λ × mean distance to the 5 nearest population decks in the pilot's embedding
  (averaged over deals, weighted over the support; 1 = the population's median spacing), and `--edit-head`:
  a pointer head on the frozen encoder scoring add / remove for every card (cross-attention initialized
  from the pilot's), trained by regression on every climb step's scored swaps and proposing half of each
  step's swaps. `--common-deals`: the value scorer's deals seeded by (opponent, deal) instead of the
  candidate's position. `rl/tests.py` checks the head's shapes, 120 proposals for legality and the
  novelty scale (PASS). Runs (`runs/head_novelty_run.sh`): log #34's settings (cold:16, seed 3, 8
  iterations, 48 games per pair, 4 new decks, 120 s search) under the scratch pilot (#42), four arms:
  base, head, novelty 0.03, both; panels of the four runs' supports plus the 24 archived lists, 60 games
  per pair, under the scratch pilot and under result #1's pilot (`notes/data/eval/hn_panel_{scratch,orig}.json`).
- **Evidence:** In the search, head swaps improved the value more often than random swaps in every
  iteration (head arm mean 67% against 47%; both arm 61% against 45%) and gave each step's best
  candidate in most iterations, but scoring the states halved throughput (29,310 candidates per search
  against 57,310). Equilibrium decks (Pokémon / Trainers / Energy): base 20 / 6 / 34 (0.87),
  head 21 / 4 / 35 (0.52), both 17 / 7 / 35 (0.73), novelty one deck at 1.00, Wigglytuff + Magmar
  10 / 24 / 26 with 4 Super Potion, 3 Bill, 3 Energy Retrieval. Against the archived field (scratch
  pilot / result #1's pilot): base 55.3 / 38.7%, head 47.3 / 30.1, novelty **70.2 / 45.7**, both
  50.5 / 30.5; exploitability in the panel 0.81 / 0.76 / 0.62 / 0.70 (scratch pilot). The novelty
  mixture beats base, head and both 80.9, 65.0, 69.8% (scratch) and 63.8, 76.8, 75.2% (result #1's
  pilot) and holds 0.42 of the panel's Nash under the scratch pilot.
- **Found:** (1) The value search's attractor is a Pokémon pile with 34+ Energy and almost no
  Trainers, even under the human-free pilot. The edit head learns the scorer's preferences and so
  reaches that attractor faster: more optimization pressure on the same proxy, worse real decks. The
  novelty bonus pushed the search off it and found a Wigglytuff deck with a Trainer package, the
  field's most-played archetype (10 of 24), in its first iteration. One seed: replication running
  (`runs/hn_replicate.sh`). (2) The value scorer's deals depended on a candidate's position in the
  batch, so the same deck scored with a standard deviation of 0.018-0.026 across positions, as large as
  real one-card swaps (0.022-0.038): the greedy value search of result #1 and logs #34-41 partly chased
  deal luck. With `--common-deals` the same deck scores identically and swap differences shrink to
  0.013-0.023. (3) The pilot's count embedding (`aux`, one row per count) is still at its random
  initialization in both pilots (rows identical between them at every count), so counts are read
  through fixed random vectors with no order; counts never seen in training (archived lists hold at
  most 19 of one basic Energy, result #1's builder reached 31) map to arbitrary vectors. A plausible
  part of #36's Energy overrating, not tested. (4) A loop variable in the head's statistics shadowed
  the proposal count, so the first head and both runs proposed 8 decks an iteration; they were rerun
  (the buggy runs are in `runs/hn-buggy/`). The rerun of both also dropped no-op swaps from the head's
  data, which the head arm did not.
- **Next:** Seeds 4-5 of base and novelty, and both with common deals (running). If novelty holds,
  make it the default and tune λ (or adapt it, DvD); try an ordinal count encoding (count as a number
  plus a thermometer code) in the next pilot. Keep the edit head only as a proposal source under a
  pessimistic or trust-region acceptance. Phase B started in parallel: the Birds list and the 2005
  legal pool (engine branch `worlds-2005`).

### #44 · 2026-10-07 · B1 / B2 · Worlds 2005: Birds and ZapTurnDos build and play; the legal pool
- **Done:** Engine branch `worlds-2005` (worktree `../ryuu-play-worlds2005`, local, not pushed; the
  submodule pin is unchanged): Scott, Mr. Stone's Project, Battle Frontier (EM), Rayquaza ★ (DX)
  (`b5f6974`); Voltorb, Electrode, Steven's Advice (HL), Dual Ball (MA), Electrike, Manectric, Master
  Ball, Space Center (DX) (`d297403`); TV Reporter, High Pressure System, Mr. Briney's Compassion (DR),
  Island Cave, Desert Ruins (HL), Rocket's Admin., Copycat, Rocket's Mission, Swoop! Teleporter,
  Pokémon Retriever, Pow! Hand Extension (TRR), Strength Charm (DX) (`e78cb4e`); fixes to Slaking RS's
  Lazy (`74a4662`), EXP. ALL RG (`e9229e1`) and Rain Dish SS (`b213f41`). Main repo (`9f4c979`,
  `3ae9a72`): `notes/scripts/ryuu_legal_pool_2005.py` (legal pool from set codes),
  `notes/scripts/ryuu_2005_cards_tests.js` (interaction checks, expected values written from the
  printed text first), `notes/scripts/ryuu_2005_env_preload.js` (verification-only coin-flip cap), and
  2005 set codes in `notes/scripts/ryuu_coverage_season.py`. Done by a background agent; checked here.
- **Evidence:** 110/110 engine specs on the new and touched cards; 27/27 interaction checks (rerun
  independently in this session: 27/27); card-data check 0 mismatches on the new cards, and 2 left of
  279 RS/SS/RG/DX/EM Pokémon after re-pairing printings (Aggron ex Weakness order, cosmetic; Clefable ex
  stage, likely a data error). `verify_enumerator` with the preload: 50 Birds mirror games and 50 Birds
  vs ZapTurnDos games, all finished, 0 engine errors, 0 mismatches over ~14,700 decisions and ~4,900
  prompts. Legal pool (RS–EM, POP 1, Trainer Kit 1, promos 1–27; Trainer Kit 2 left out as released
  March 2006): 1,014 printings, 959 distinct cards; the engine has 384 printings (340 cards), RS, SS and
  RG complete. Coverage: Birds 60/60, ZapTurnDos 60/60 (one name alias), ZRE 54, Blastoise ex 51,
  Nidoqueen 51, Blaziken 47.
- **Found:** (1) The local pokemon-tcg-data cache held Ruby & Sapphire under Sandstorm's file; refetched,
  which cleared every list's unresolved count (the cache is gitignored). (2) A hang in the env, not the
  engine: `env/engine.js` `trial()` forces every coin flip to one side, so "flip until tails" attacks
  (Rayquaza ★'s Spiral Rush, Linoone RS) never end; the first 50-game check ran 37 min before it was
  killed. The env fix waits for the running experiments (they load `env/`). (3) An audit of existing
  EX cards found six more text mismatches, not yet fixed: Wally's Training, Rare Candy SS (refuses a
  Stage 1), Electrode ex's Extra Energy Bomb, Squirtle RG's Smash Turn, Blaziken RS's Fire Stream,
  Blastoise ex's Energy Rain. (4) The env still uses the 2000 rules object; 2005 first-turn rules are
  not configured. The builder must enforce one Pokémon ★ per deck.
- **Next:** The flip cap in `env/engine.js`; the six audit fixes; 2005 rules in the env; then ZRE
  (Magmar TRR, Rayquaza ex DX) and Blastoise ex / Nidoqueen; push `worlds-2005` to the fork.

### #45 · 2026-10-07 · B2 · Worlds 2005 engine under more tests: a fuzz, one engine hang fixed
- **Done:** `notes/scripts/ryuu_2005_fuzz.js`: seeded SimpleBot games between random legal decks drawn
  from all 340 2005-legal cards the engine has (card-agnostic shape: 2-3 Pokémon lines with their
  evolutions, 13-19 basic Energy of their types, 0-3 Special Energy, random Trainers, one Pokémon ★),
  forcing a random attack or Trainer on 30% of turns, with `--only N` to trace one game and a
  diagnosis of stuck positions. Engine `worlds-2005` `47a7676`: Signs of Evolution (Caterpie RG,
  Wurmple RS, Eevee SS) trims an illegal choice (mixed lines, a repeated name) to a legal one instead of
  asking again, with a spec; rebuilt the sets and SimpleBot packages in the worktree (its build
  predated the last commit). Fixed a harness flaw in the fuzz and in `ryuu_promo_fuzz.js`: after a
  rejected forced action the store restores its backup as a new State object, and the loop let the
  bots decide on the stale, half-applied one.
- **Evidence:** Full sets spec suite on `worlds-2005`: 801/801 (the agent had run 110). The 2000
  checks on `worlds-2005`: 68/68 interaction tests and 23/23 rulings, as on `sts-2000-pool`. The
  agent's 27 interaction checks: 27/27. The new Caterpie spec fails on the old code and passes on the
  fix. Fuzz, 1,500 games: first run hung at game 10 (profiled with `node --prof`: the loop was in Signs
  of Evolution under SimpleBot's attack simulation); after the engine fix 1,481 finished, 16 stuck and
  3 errors, all traced to the harness flaw; after that fix 1,500/1,500 finished in 123 s, with 456 of
  483 attacks and 55/55 Trainers accepted at least once (the 27 never reached are mostly fossil
  Pokémon, which the random decks do not build). `verify_enumerator` with the preload, 300 Birds /
  ZapTurnDos games: 0 engine errors, 0 mismatches over 43,004 decisions and 15,347 prompts. Promo fuzz
  (2000) after its fix: 400/400.
- **Found:** "Ask again until the answer is legal" loops forever under a deterministic chooser; the
  remaining prompt loops in the sets are coin-flip loops (Rayquaza ★, Linoone RS, Blastoise ex RG,
  capped, and Geodude FO, a Base-era card). Geodude FO's "flip until tails" also hangs the env's
  forced-flip legality trial, so the A5 full pool can hang the 2000 env too, not only 2005 decks.
- **Next:** The flip cap in `env/engine.js` once the running experiments finish; fossil lines in the
  fuzz's decks; the six audited EX text fixes.

### #46 · 2026-10-07 · A5 / A1 · Novelty does not replicate as a clear win; the env's flip cap; a correction to #43
- **Done:** `runs/hn_replicate.sh`: base and novelty 0.03 at seeds 4 and 5, and both at seed 3 with
  `--common-deals`, all with #43's settings under the scratch pilot; one panel of the eight runs'
  supports plus the 24 archived lists, 60 games per pair, under the scratch pilot and result #1's pilot
  (`notes/data/eval/hn_rep_panel_{scratch,orig}.json`). `env/engine.js` `trial()` now forces a coin
  flip to one side at most 32 times in a row (`MAX_SAME_FLIPS`, exported), so "flip until tails"
  attacks end; `notes/scripts/ryuu_2005_env_preload.js` keeps its own copy only for engines without it.
- **Evidence:** Against the archived field (scratch pilot / result #1's pilot), base vs novelty: seed 3
  56.2 / 40.5 vs 71.8 / 43.3; seed 4 42.2 / 32.1 vs 58.4 / 34.2; seed 5 60.4 / 39.6 vs 53.6 / 36.6;
  seed 3 with common deals 43.2 / 31.8 vs 50.6 / 35.9. Novelty is ahead in 3 of 4 pairs under both
  pilots, by a mean of 8.1 points under the scratch pilot and 1.5 under result #1's. Main equilibrium
  decks (Trainers / basic Energy): novelty seed 3 24 / 21, seed 4 2 / 36, seed 5 2-7 / 32-35, seed 3
  with common deals 7-18 / 27-33; base seed 5 found a 19 / 24 Hitmonchan / Magmar deck without novelty.
  The seed-3 novelty mixture holds the whole Nash of the eight-run panel under the scratch pilot.
  Common deals (seed 3): base 43.2 against 56.2 without, novelty 50.6 against 71.8. Flip cap:
  `trace_hash` over 300 seeded 2000 games identical before and after (e332007...); `test_env` 100
  games PASS; `verify_enumerator` 50 Birds / ZapTurnDos games PASS on the env's own cap.
- **Found:** (1) Correction to #43: its deck counts took any card with "Energy" in its name as Energy,
  so Energy Retrieval and Energy Removal were counted twice; the seed-3 novelty deck is 15 Pokémon /
  24 Trainers / 21 basic Energy, not 10 / 24 / 26 (#43's other decks were also slightly off). (2) The
  Trainer-rich deck was mostly seed luck: in seeds 4 and 5 novelty also converged on 32-36 Energy, and
  base found a Trainer deck on its own at seed 5. Novelty helps on average, modestly and not reliably;
  #43's headline overstated it. (3) Removing the deal noise made both arms worse at seed 3 (one seed):
  consistent with #43's edit head, more accurate optimization of this pilot's value gives worse real
  decks, so the noise was acting as a regularizer. The bottleneck is the objective (the pilot's value),
  not the search.
- **Next:** Improve the objective before the search: a stronger human-free pilot with an ordinal count
  encoding, and pessimistic / trust-region acceptance against real games. Keep novelty on as a cheap
  default; drop the edit head and common deals from the default until the value is better.

### #47 · 2026-10-09 · A5 · Edit head combined with the value: no mode beats novelty alone (backfilled)
- **Done:** `--head-mode screen | combine | agree` in `rl/search.py` / `rl/psro.py` (commit `c5fbc80`):
  ways of using the edit head together with the start-of-game value. `runs/head_modes_run.sh`: each
  mode at seeds 3, 4 and 5 with novelty 0.03 and #43's settings (pilot-scratch it249, cold:16, 8
  iterations, 48 games per pair), against novelty alone (`runs/hn-nov`, `hn-nov-s4`, `hn-nov-s5`).
  Panel of the twelve runs' supports plus the 24 archived lists, 60 games per pair, under the scratch
  pilot: `notes/data/eval/hm_panel_scratch.json` (run 2026-10-07; logged here 2026-10-09).
- **Evidence:** Against the archived field (s3 / s4 / s5, mean): novelty alone 70.9 / 59.2 / 53.7, 61.3;
  screen 58.1 / 42.1 / 52.3, 50.8; combine 54.4 / 41.7 / 59.0, 51.7; agree 57.4 / 51.4 / 50.2, 53.0.
  8 of the 9 head-mode runs are below novelty alone at the same seed (combine s5 is above). Staple
  Trainers per final mixture (Computer Search, Item Finder, Oak, Bill, Gust, PlusPower, Energy Removal,
  Super Energy Removal; the archived mean is 20.0): novelty s3 8.0, every other run 0-2. The panel's
  Nash: archived 0.70, novelty s3 0.30, all head-mode runs 0.
- **Found:** As in #43 and #46, optimizing the pilot's value harder makes real decks worse; no way of
  combining the edit head with the value avoids that. Consistent with #46: the objective is the limit.
- **Next:** Keep the edit head off (#46). Pilot improvements (#48).

### #48 · 2026-10-09 · A4 · pilot-v2: a larger human-free pilot reaches 83% against SimpleBot (backfilled)
- **Done:** Ordered count features for the token model (`--count-features`, commit `d42f4b8`); the env
  runner asks all agents at once instead of one at a time (`notes/scripts/patch_runner_concurrent.py`,
  applied in `6e065c7`). `runs/pilot_v2_run.sh`: pilot-v2, trained from scratch on #42's random decks
  (no archived lists), with d 256, 4 layers, 8 heads, count features, a league, deck-out wins 0 and
  3.24M parameters (#42: 1.6M). Evaluated against SimpleBot on the archived decks every 25 iterations
  (evaluation only, 400 games).
- **Evidence:** Against SimpleBot (± ~0.04): it24 49.5%, 49 58.8, 99 55.9, 149 77.0, 199 81.5, 249 79.7,
  299 83.3, 324 83.1, 349 83.3. #42's pilot at it249: 78.7%; pilot-v2 at it249 is the same within
  error, and gains about 4 points by it299. Collection time grew from 10 s to 30 s an iteration as
  league snapshots were added. The run stopped at iteration 371 of 400 (log ends 2026-10-08 00:04;
  the cause was not recorded). Its diagnostics (`pilot_diag.py`) and the count-features-only run
  (`pilot-cf`) never ran, so the effect of the count features alone is not measured.
- **Found:** Doubling the model and adding count features gave a few points at most, and it
  plateaued near 83% from it299. Size is not the main limit.
- **Next:** Find where it loses (#49); diagnostics for it349.

### #49 · 2026-10-09 · A4 · Best-of-9 ceiling, and an attention-architecture test (backfilled)
- **Done:** `runs/ceiling/`: pilot-v2 it349 against SimpleBot on 960 deals (24 archived decks × 40),
  once greedy and 8 times sampled on the same deals (`evaluate.js --seed`), and
  `notes/scripts/ceiling_by_deck.py` for the best of the 9 per deal. `runs/arch_test.sh`: on the 6
  decks with the largest gap, four variants fine-tuned 30 iterations from it349 against SimpleBot in
  mirrors: A same architecture, B +2 cross-attention blocks, C candidates attend to each other, D both
  (`--cross-layers`, `--cand-self`, commit `6e065c7`; new blocks start as the identity). Diagnostic
  only: it trains on archived lists, so no weights from it go back into the pipeline.
- **Evidence:** Ceiling: greedy 82.9%, best-of-9 97.6%, 23 deals never won; largest gaps Froelich
  Wigglytuff 0.275, Jay Yu Wigglytuff 0.250, Bartlett Sponge 0.250, Viray Rain Dance 0.250, Diamond
  Articuno/Hitmonchan/Scyther 0.237, Pratt Wigglytuff 0.200. Against SimpleBot, 480 games each (target
  decks mirrored, seed 77 / all 24, seed 78): it349 74.4 / 81.7; A 91.0 / 89.6; B 88.8 / 88.7; C 88.2 /
  90.0; D 89.5 / 91.5 (± 0.025-0.039).
- **Found:** (1) The ceiling overstates what better choices can gain: later shuffles and coin flips
  follow the actions taken, so some best-of-9 wins are luck (the script says so). (2) All four
  variants gain 14-17 points on the target decks and 7-10 on all 24 from 30 iterations on those decks,
  and differ from each other within error. Extra attention is not what is missing; experience on the
  decks is, and archived decks cannot be used for that. (3) In chat on 2026-10-09 these four results
  were first described without saying they were fine-tunes on archived decks.
- **Next:** Play-time search over the pilot (psearch, #50), which needs no training on any deck.

### #50 · 2026-10-09 · A4 · psearch: beats its own greedy pilot, not SimpleBot
- **Done:** `PolicySearchAgent` (`env/agents.js`, `psearch:<onnx>:k:dets`, commit `b7db8ea`; fix
  `b83d6b0`, candidate moves matched by key in each re-dealt copy because re-dealing can change which
  moves exist). At each decision with 2 or more moves (not prompts) it takes the pilot's top k moves,
  plays each in `dets` copies with the hidden cards re-dealt, finishes the turn with the greedy pilot,
  and picks the best mean end-of-turn value (±1 for a finished game). `runs/psearch_test.sh`:
  psearch k 4, dets 4 over pilot-v2 it349, against SimpleBot on the seeds of #49's greedy evaluations
  (same opening deals), and head to head against greedy it349. CPU only, 14 workers × 1 ONNX thread.
- **Evidence:** Against SimpleBot, 480 games each, 0 errors: target decks 71.7% ± 4.0 (greedy, #49:
  74.4 ± 3.9); all 24 decks 82.5% ± 3.4 (greedy 81.7 ± 3.5). Paired by opening deal: target 278 won
  by both, 79 by greedy only, 66 by psearch only, 57 by neither; all 24: 343 / 49 / 53 / 35. Head to
  head against greedy it349, all 24 decks: 65.4% ± 6.0 (n 240; by direction 69.2 / 61.7), mean 207
  steps a game. Wall time 36 / 40 / 24 min, against ~2 min for a greedy evaluation of the same size.
- **Found:** (1) psearch gains nothing against SimpleBot, on the decks with the largest ceiling gap or
  overall, but beats its own greedy policy. The search scores lines with the same network it is
  compared against: it finds what that policy misplays, which does not transfer to an outside
  opponent. Expert iteration on this operator could therefore climb against itself without getting
  generally stronger. (2) The one-turn horizon and the value head's errors (#36) are the likely limits;
  not separated here. (3) Same opening deal is not a full pairing: later shuffles follow the actions
  taken, so the per-deal counts are noisy.
- **Next:** Before expert iteration on psearch: psearch against an independently trained pilot (log
  #42's pilot-scratch) in both directions, and dets 8 to separate re-deal noise. Use opponents the
  agent did not train against (past snapshots, other runs) as the general measure, since gains
  against itself can be non-transitive.

### #51 · 2026-10-09 · Design · Search in action-sequence space; generality of the method
- **Done:** `notes/design-action-sequence-search.md`: a causal (prefix-LM) transformer over the root
  state tokens plus action and outcome tokens, Gumbel MCTS in that space with chance nodes from an
  outcome head, and expert iteration on the search's visit counts; a sequence logger for both
  players' views without hidden information; steps with gates (k-step accuracy; equal-compute
  comparison with psearch; expert iteration; engine-free search). A Generality section lists the
  Pokémon-specific parts to replace for other TCGs: fixed slot tokens, Pokémon verbs and slot indices
  in actions, hand-picked card fields, and the deck-out reward (`--deckout-win 0`, game-specific
  shaping). Agreed scope (Evan, 2026-10-09): a general self-discovery method for TCGs, so no training
  on archived lists and no hand-written bots as training opponents; both are evaluation only.
- **Evidence:** Design only; nothing built or measured.
- **Found:** The arch-A..D fine-tunes (#49) trained on archived lists against SimpleBot, which the
  scope rules out except as one-off diagnostics. #50's result raises the bar for step 2's gate:
  matching psearch is not enough, since psearch does not beat SimpleBot.
- **Next:** #50's checks; then expert iteration with the plain game result as reward if the search
  gain transfers; general metrics (Elo against past snapshots, exploitability, deck sensitivity).

### #52 · 2026-10-10 · A5 / A4 · Co-evolution: the pilot trains only on decks the system drafts, over the full pool
- **Done:** `rl/coevolve.py`: one process holds the learner, its optimizer, its league and one set of
  workers, used for both training and the matchup matrix (`GpuMatrix.attach`). Each round: (1) every pair
  of the population is measured under the current pilot (24 greedy games per pair) and the meta game
  solved; decks out of the support leave once the population passes 48 (`retired.jsonl`); (2) the value
  search with novelty 0.03 proposes 4 decks, and of 64 fresh exploration decks the 2 the pilot rates best
  join the population; (3) 10 PPO iterations, each on 256 matchups drawn anew: sigma vs sigma 0.4, this
  round's new decks vs sigma 0.2, any population deck vs sigma 0.15, exploration decks vs sigma or each
  other 0.25. `rl/deckgen.py`: random decks in two shapes, half each, `lines` (Pokémon lines with
  typed Energy, as `pilot_decks.py`, plus Special Energy, which no earlier generator drew) and `flat`
  (only the format's rules: a Dirichlet split of Pokémon / limited cards / basic Energy, at least one
  Basic), every non-Energy card drawn with weight (1 + training games it was in) ^ -0.5, so the least
  seen cards come up most; `Coverage` logs the share of the pool in the population, in the support and
  in 200+ training games, and the entropy of card exposure. Reward is the plain game result
  (`--deckout-win 1`, per #51); lr 1e-4 from pilot-v2 it349; full pool (277 cards); SimpleBot on the
  archived decks every 5 rounds is evaluation only. `RemotePool.pace` rests 0.25 x each served batch's
  GPU time: the first launch measured at 84-91% GPU (pilot-v2 is twice #31's model), and was stopped.
  Engine (fork `8fe233c`, local): Rattata TR's Trickery can't be used with an empty deck (it swapped
  `undefined` into the Prizes, crashing the next effect pass); Dark Gyarados TR's Final Beam no longer
  throws when knocked out while Asleep/Confused/Paralyzed (it aborted the attacker's attack). Launch:
  `runs/coevo_run.sh` (`runs/coevo-1`, 30 rounds, seed 1), running.
- **Evidence:** Generator: 2,000 decks all legal, all 277 cards used, basic Energy 0-56 (median 20).
  Random-policy games between full-pool decks (6 sets of 60 decks, 610 games each): before the fixes 16 of
  360 decks were in a crashing game (Rattata TR in most), after them 3,660 games with 0 errors. New specs
  fail on the old code (3/3) and pass on the new; sets suite 692/692; `test_env` 100 games PASS;
  `verify_enumerator` 200 games PASS. Smoke run (6 decks, 2 rounds, 2 PPO iterations each): measure,
  draft, PPO, SimpleBot evaluation and checkpoint all run; coverage after 2 rounds 55% of the pool in the
  population, 25% of cards in 200+ games. Paced, the search phase sits at ~32% GPU.
- **Found:** No earlier experiment played the full pool: the A5 "full pool" had never been run, and the
  field pool hid both card bugs (neither card is in the 56). Every earlier random-deck generator left out
  Special Energy, so Double Colorless Energy could only enter a deck by a swap. The starting pilot
  (pilot-v2) learned on the field's 56 cards, a pool chosen from the archived lists; co-evolution moves it
  off that pool, but its weights still carry it.
- **Next:** Watch `runs/coevo-1`: card coverage, support Energy counts, SimpleBot every 5 rounds, the
  ending mix under the plain reward; then the answer-key panel against the archived field and a second
  seed.

### #53 · 2026-10-10 · A5 · coevo-1: every card explored, but the meta collapsed to one deck type (stopped at round 23)
- **Done:** `runs/coevo-1` (#52's settings) ran rounds 0-23, 240 PPO iterations, and was stopped there by the
  user's choice once it had answered its question, to free the machine for the league (#54). Its log,
  population, retired decks and a pilot per round are in `runs/coevo-1/`.
- **Evidence:** Coverage: every allowed card in 200+ training games by round 4; least-seen card 2,300 games
  by round 23 (median 5,374). The share of the pool in some population deck rose to 83% (round 5), then
  fell to 55% (round 23) as random decks were retired. Equilibrium: 1 deck in rounds 0-4, 8 and 23, 2-5
  otherwise; from round 7 every support deck held Hitmonchan, Scyther and Chansey (checked per round
  from the population and `retired.jsonl`). The three support decks of round 15 differed by 10-16 cards
  (10 is the search's minimum); of the population then, 30 of 33 search-built decks were within 22 cards
  of a support deck and all 18 exploration decks 40-60 cards away, and an exploration deck held weight
  only once (round 5, 0.18). Training endings: deck-out 2-8% and prizes 39-58% in rounds 0-4; deck-out
  41% and prizes 23% at round 13; deck-out 35%, prizes 34%, 185 decisions a game in rounds 22-23 (106-125
  in rounds 0-4). SimpleBot on the archived decks (evaluation only, 400 games): round 4 76.8% ± 4.1,
  round 9 78.5 ± 4.0, round 14 82.8 ± 3.7, round 19 80.5 ± 3.9 (pilot-v2 at the start 83.3). Equilibrium
  decks: round 13-14 `r11-s0`, 9 Pokémon / 20 Trainers / 31 basic Energy with 4 Energy Removal, 3 Super
  Energy Removal, 3 Devolution Spray, 4 Bill, 4 Oak, 2 Computer Search; round 19 `r16-s0` with 4 Double
  Colorless Energy and 4 Potion Energy, 28 basic Energy, 4 Energy Removal, 4 Oak, 2 Computer Search;
  round 23 `r21-s0`, 11 Pokémon / 16 Trainers / 31 basic + 2 DCE, with 4 Energy Removal, 4 Oak, 3
  Computer Search, 3 Pokémon Center, 2 Bill. GPU: the PPO update ran in bursts of 89-95% (mean ~65%),
  above the 80% cap; the other phases stayed under it.
- **Found:** (1) The cards were explored, the deck types were not: the value search proposes variants of
  the leading deck (half its restarts start from a support deck, and confirmation games against the
  support favor near variants), exploration decks compete raw and are retired, the one pilot plays the
  leading deck best (40% of its games are support against support; #40 measured 11 points from this), and
  retirement removes only decks without weight. (2) Under the plain game result, self-play found an
  Energy-denial and stall deck (Energy Removal, Super Energy Removal, Chansey walls, wins by deck-out);
  deck-outs rose to 41% of training games, then fell back to 25-35% without any change. The deck shares
  its disruption package with the archived Sponge lists (Energy Removal, Super Energy Removal, Chansey,
  Scyther, Oak, Computer Search), but plays 28-35 basic Energy against their 12-21. (3) Staples came back
  without any human input: Computer Search (dropped by every earlier value search), Scyther, Oak, Energy
  Removal, Super Energy Removal, and from round 16 Double Colorless Energy. (4) Neither the SimpleBot
  dip nor its recovery is outside the error: training on its own drafted decks did not cost the pilot
  strength against an outside opponent. (5) The "nearest archived list" labels are misleading at these
  overlaps (0.3-0.4): decks labeled Wigglytuff-like or Clefable-like hold neither card.
- **Next:** A population of deck-owning agents, so other deck types get developed and piloted before they
  are judged (#54).

### #54 · 2026-10-10 · A5 · A league of deck-owning agents: built, tested, launched
- **Done:** `rl/league.py` (the user's proposal: several agents with their own value heads do the metagame,
  so it is league training rather than one agent's self-play). One agent-conditioned network
  (`rl/token_model.py` `n_agents`: an agent embedding added to every token and one value head per agent,
  both starting as the loaded checkpoint, `init_agents_from_base`, `copy_agent`; NeuPL-style) holds 3 main
  agents, 2 exploiters and a generalist. Each main and exploiter owns a deck lineage: every round it
  climbs its own deck by its own value against its opponents (mains: the equilibrium; exploiters: the
  mains' part of it), at most 12 (exploiters 24) cards a round and at least 20 cards from every other
  agent's deck, and real games (its own agent piloting, each opponent its own) adopt the best finalist
  only if it beats the current deck by 2 points. Exploiters that beat the mains' mix at 60% are frozen into
  the league and restart from a fresh random deck with the generalist's embedding and value head; after
  4 rounds without a better deck, or 8 rounds, they restart without being frozen. Every 3 rounds the
  mains' strategies are frozen (deck, agent, snapshot of the network); the league keeps at most 12 frozen
  strategies. The meta game is over (deck, pilot) strategies, each side piloted by its own agent;
  frozen pairs are cached. PPO: each live agent gets the same number of matches per iteration and only
  its own side is recorded, with its agent id. The generalist owns no deck, plays league and
  exploration decks, and is what the SimpleBot check plays. Plumbing: `rl/remote.py` `AgentView` (views
  of one network are served in one forward pass with an agent id per row); `env/remote_worker.js` a
  `league` command and per-deck pilots in `games` and `values`; `env/runner.js` records each transition's
  model slot; `rl/train.py` passes agent ids to the update, paces it per micro-batch, and takes
  `gpu_load` (0.7 here, against coevo-1's bursts). `rl/league_tests.py`. Launch: `runs/league_run.sh`
  (`runs/league-1`, 30 rounds, from pilot-v2 it349, full pool, plain game result), running.
- **Evidence:** `rl.league_tests` PASS: a 6-agent network loaded from pilot-v2 gives pilot-v2's logits and
  values for every agent (random states, within 1e-5); per-row agent ids equal `fixed_agent`; changing one
  agent changes only its rows; `copy_agent` copies; the ONNX export of one agent matches PyTorch; merged
  serving of two agents' requests equals separate forward passes. `rl.tests` PASS; `test_env` 100 games
  PASS; `verify_enumerator` 200 games PASS; a coevolve smoke run still works. League smoke runs (2 mains,
  1 exploiter, 4 rounds with a resume from round 2): measuring, caching, freezing, exploiter resets,
  retirement, drafting with real-game adoption, PPO and the generalist's ONNX evaluation all run.
- **Found:** Recording both sides of every match gave the leading deck's agent 20-23k of each iteration's
  transitions against 2-5k for the others (it is everyone's most likely opponent), which would rebuild
  coevo-1's co-adaptation inside the league; with only the focal side recorded the agents get 2.9-6.5k
  each.
- **Next:** Watch `runs/league-1`: deck types in the support (decks 20+ cards apart), exploiter successes,
  coverage, the generalist against SimpleBot, endings; then compare with coevo-1 on the same measures and
  the answer key.

### #55 · 2026-10-10 · A5 · The league with a separate network per agent
- **Done:** By the user's choice after counting #54's parameters, `rl/league.py` now gives every agent a
  network and an optimizer of its own (`SeparatePilots`, the default; AlphaStar-style): each starts as a
  copy of pilot-v2 it349 and trains only on its own matches, the batch split per agent by `subset` (legal
  ids re-indexed). A frozen strategy is a snapshot of its one agent's network; an exploiter restarts as a
  copy of the generalist's network with a fresh optimizer. `--shared` keeps #54's design (`SharedPilots`).
  `runs/league-1` (shared) was stopped in round 0. Launched `runs/league-2` (separate networks, 30 rounds,
  seed 1, otherwise #54's settings) with `runs/league_run.sh`.
- **Evidence:** #54's network had 3.64M parameters: card embedding 197k (5.4%), token inputs 101k (2.8%),
  state encoder 2.11M (58%) and policy 762k (21%), all shared; each agent owned a 256-number embedding and
  a 67k value head (1.8%), so the agents' policies differed only through the embedding. `rl.league_tests`
  PASS, now including `subset` (each kept row keeps its own legal ids, token fields and scalars). Smoke run
  with separate networks, 4 rounds with a resume from round 2: per-agent PPO statistics, per-agent
  snapshots (`r001-a0.pt` ...), the generalist's ONNX evaluation; the shared mode still runs (1 round).
- **Found:** In league-1's only round, all five specialists adopted drafted decks on real games; the two
  exploiters went from 0.00 and 0.06 to 0.94 and 0.81 against the leading main agent's deck.
- **Next:** As #54, on `runs/league-2`.

### #56 · 2026-10-10 · A5 · League drafting: a two-stage adoption check, against the winner's curse
- **Done:** In `rl/league.py` the real-game check of a specialist's drafted deck now has two stages: the
  finalists and the current deck play at least `--confirm-min` 96 games each, spread over the opponents
  (more per opponent when there are few), the best finalist is picked, and only it is re-tested against
  the current deck on fresh games; it replaces the deck only if it wins the re-test by `--adopt-margin`
  (2 points). The log keeps both stages (`current_real`, `best_real`, `recheck_current`, `recheck_best`).
  `runs/league-2` was stopped in round 1 and relaunched clean as `runs/league-3` (same settings).
- **Evidence:** In league-2 every specialist adopted its best finalist in both rounds (10 of 10) on 16
  games against a single opponent, about ±12 points of noise per estimate, and picking the best of 4
  noisy finalists makes the winner beat the current deck by 2 points even when none is better. Smoke
  run (2 mains, 1 exploiter, 24 games): stage-1 and re-test estimates of the same deck differed by up to
  25 points (m0's current deck 0.29, then 0.54), and the re-test numbers fell toward the current deck's.
- **Found:** The smoke run was first started while league-2 was still running, about 10 minutes over the
  machine's load cap (20 node workers), until league-2 was stopped.
- **Next:** As #54, on `runs/league-3`.

### #57 · 2026-10-10 · A5 · league-3 rounds 0-7: three deck types in the equilibrium; restarting exploiters now stay in the league
- **Done:** `runs/league-3` (#56's settings) ran rounds 0-7. In round 8 exploiter `e0` reached its 8-round
  limit and restarted while its deck held 0.33 of the equilibrium, and the league dropped that deck. The
  run was stopped, `rl/league.py` changed so that an exploiter restarting without success is frozen first
  whenever its deck has equilibrium weight, and resumed from the round-7 checkpoint (`--resume`; the
  round-8 measurement came out identical, and `e0.0.v4@r8` was frozen before the restart).
- **Evidence:** Adoptions by round (two-stage check): 5/5, 4/5, 3/5, 3/5, then fewer; in round 1 the leading
  main kept its deck (best finalist 0.33 against its current 0.55 in real games). Training endings: deck-out
  43% / prizes 43% in round 0, then prizes 75-84% and deck-out 3-8% from round 2 (82% / 4% in round 4).
  Equilibrium: one deck in rounds 0-6, the lead alternating between the `m0` and `m1` lineages
  (m0, m1, m0, m1, m1, m0); round 7: `m0.v4` 0.43, `e0.0.v4` 0.43, `m2.v6` 0.14, three deck types (26-59
  cards apart); round 8: `m1.v4` 0.56, `e0.0.v4` 0.33, `m0.v4` 0.11. Decks (basic Energy / Pokémon /
  Trainers): leaders 14/15/31 (round 1), 25/22/13 (round 2), 20/20/20 (round 3); by round 6 `m0.v4` 29/24/7
  (Arcanine, Growlithe, Magmar, Jigglypuff, Chansey), `m1.v4` 34/24/2, `m2.v6` 32/28/0 (Charmander,
  Magmar, Ponyta, Exeggutor), `e0.0.v4` 36/23/1 (Hitmonchan, Machoke, Mr. Mime, Snorlax). Generalist
  against SimpleBot on the archived decks after round 4: 76.0% ± 4.2 (coevo-1's pilot at round 4: 76.8%).
  Exploiter `e1.0` restarted at round 7 (0.22 against the mains). Rounds take about 13 minutes; GPU in the
  update about 63% mean, 78% at most.
- **Found:** (1) Unlike coevo-1, the league keeps several deck types in its equilibrium and plays prize
  races, not a stall game. (2) But the lineages shed Trainers round after round, ending as Pokémon and
  Energy piles (0-7 Trainers, 29-36 basic Energy) that win real games against each other under these
  pilots; the archived lists play 26-30 Trainers, and coevo-1 had kept Computer Search, Oak and Energy
  Removal. A specialist's pilot learns from a sixth of the games; whether it uses Trainers worse than
  coevo-1's one pilot is not measured.
- **Next:** Watch league-3 to round 30; then measure how much each specialist gains from Trainers (card
  ablations on its own deck), the generalist on the specialists' decks, and both runs against the answer key.

### #58 · 2026-10-10 · A1 / A5 · A free cycle through a confirm prompt: fixed in the env, league-3 resumed
- **Done:** From round 13, league-3's training games grew from ~220 to ~500 decisions and games cut off at
  the 5,000-step cap from ~0.5% to 5-6% a PPO iteration, while the mean policy entropy fell from 0.40 to
  0.16; the run was stopped in round 14. `notes/scripts/league_loops.py` (rebuilds a league checkpoint,
  plays one batch of training-style games, counts cut-off games by agent and deck pair, exports the
  agents as ONNX) and `notes/scripts/trace_loop.js` (prints a long game's repeated decisions) found the
  cycle: exploiter `e1.1` (agent 4) used Tentacool FO's Cowardice and answered its confirm "no", which
  leaves the state as it was, 2,400 times in a game. A game cut off at the cap is a draw (0), better than
  a loss (-1). `env/game.js`: a prompt's single-step answers (`res|...`), when it has at most 4, are now
  tested for no-ops like cancel and an empty done (#14, #20): an answer that replays to the state before
  the opening action is dropped, and if only such answers are left the action is a dead end. League-3
  was resumed from its round-13 checkpoint with agent 4 restarted (`--reset 4`, fresh deck, the
  generalist's network), since its network had learned the cycle.
- **Evidence:** Before the fix, 889 games of the round-13 league: 50 cut off (5.6%), 33 of them in agent
  4's 130 games (agents 0-3 and 5: 0-6 each). After it, the traced pairing (agent 4 against agent 0) that
  had run to 5,000 decisions ends in 201, and 12 of 12 games end normally. `test_env` 100 games PASS,
  `verify_enumerator` 200 games PASS, `bench_env` 65.1 random-policy games/s/core, 1,200 random games
  between full-pool decks with 0 errors and 0 cut off. The engine already enforces the card's "not the
  turn it was played" rule; the cycle was the env's.
- **Found:** The env's cycle rules covered answers that pick nothing (cancel, empty done), not a "no" to a
  confirm; any boolean or single-choice answer can undo an action in the same way. The verifier compares
  enumerated answers before this filter, so the filter itself is checked only by replay (by construction)
  and by games ending; a dedicated invariant (no state repeated within a turn) in the fuzz would catch
  the next one. The pilot's training games stayed fine for 12 rounds and the policy found the cycle once
  its deck held Tentacool and it was losing.
- **Next:** Watch league-3 to round 30; add a repeated-state invariant to the fuzz.

### #59 · 2026-10-11 · A5 · Back to basics: a repeating tournament of 3, 6 and 9 deck-owning agents
- **Done:** By the user's direction, a simpler setup than the league, `rl/tournament.py`. N agents, each with
  a network and an optimizer of its own (`SeparatePilots`; pilot-v2 it349's architecture and weights)
  and its own deck, starting from different random rules-only decks (`--p-flat 1`; same seed, so the
  N=6 run's first three decks are the N=3 run's, and so on). Every round: a round-robin tournament (32
  games a pair, each agent piloting its own deck; standings, equilibrium, cyclic triads); every agent
  redrafts its own deck at once against the field of the round's decks, up to 45 cards (75%) a round,
  with exploration in card picks (half the added cards drawn toward the least-played cards, weight
  floored at 0.25; half the climbs from a random kick; steps drawn from softmax(value / 0.03); one
  finalist drawn at random; a finalist within 3 points of the current deck on the fresh-game re-test is
  adopted with probability 0.25) and 60 value calls per agent, 16 deals per candidate spread over the
  opponents; then 8 PPO iterations, each agent playing its own deck against the others and learning
  from its own side, exactly 8,000 transitions an agent per iteration, with exploration in actions (each
  agent's entropy coefficient rises from 0.01 up to 0.05 while its policy's entropy is below 0.75).
  Before launch, a review workflow (4 lens-specific reviewers, an independent skeptic per finding:
  33 findings, 21 confirmed) found a crash (numpy integers in the logged cycle counts), unequal training
  budgets across N (games in flight overshoot the collection quota: about 1.5x the data per agent at N=3
  as at N=9), anti-imitation card weights (a card another agent plays was about 60x less likely to be
  proposed than a card nobody plays), an entropy controller that first cut exploration 10x, draft effort
  that fell with N (fixed seconds), the Pokémon-specific starting generator, and missing measures; all
  fixed. A second workflow is re-checking the fixes. `league-3` was stopped in round 15 (checkpoint at
  round 14). Launch: `runs/tournament_runs.sh`, `runs/tourn-3`, `tourn-6`, `tourn-9` (seed 1), then
  `tourn-3-s2` (seed 2, for run-to-run variance), 20 rounds each, one after another.
- **Evidence:** Smoke runs (3 agents, 2 rounds): drafts changed 9-45 cards a round; every agent trained on
  exactly its budget (from 749-1,834 collected); an exploratory adoption fired; logged rows serialize;
  the networks and an atomic checkpoint were saved. Cycle counts: a clear 3-cycle counts 1 (1
  significant), all ties 0, a 0.55 cycle 1 (0 significant).
- **Found:** pilot-v2's weights were trained on random decks restricted to the archived field's cards, so
  the starting networks carry that prior; each deck's share of field cards is logged to watch for it.
- **Next:** Compare N=3, 6, 9 on deck types, equilibrium support, cycles, drafted share, Trainers and
  Energy, staples, each agent's play against SimpleBot on its own deck, and the seed-2 N=3 run's spread.

### #60 · 2026-10-11 · A5 · Tournament fixes from a verification workflow; chain relaunched
- **Done:** A second workflow (3 checkers by fix, a skeptic per problem; 7 reported, 4 confirmed, as two
  problems) re-checked #59's fixes against the running N=3 run. `rl/tournament.py`: each climb now takes
  at most `--climb-steps` 15 value calls and an agent has `--draft-calls` 90 a round (was 60 calls with a
  40-step climb cap), and collection aims at 1.4x the total budget (`--collect-margin`) with a logged
  warning for any agent still short. The N=3 run (3 rounds done) was stopped, kept as
  `runs/tourn-3-prefix`, and the chain relaunched from the start.
- **Evidence:** In the first launch every agent-round drafted 2 climbs and 2 finalists (scored 720 = 60 x
  12): climb steps are drawn noisily, so a climb almost never stalled and ran to the 40-step cap, the
  60-call budget fit two, the random finalist never fired, and only 1 of the 2 climbs could start from a
  kick. Per-agent collection is not a floor: agent 1 trained on 7,820 of 8,000 transitions in PPO iteration
  12 (a deck with short games collects less of the shared quota). Smoke run after the fixes: 6 climbs and
  3 finalists per agent, the random finalist once the best; every agent collected 780-1,914 against a
  500 budget. The checkers confirmed the rest: cycle counts against Kendall's formula on 600 random
  tournaments; identical seeds for shared pairs at N=3/6/9; exact subsampling with legal ids, advantages
  and slots aligned; no disallowed card drawn; the entropy coefficient carried and checkpointed per
  agent; logged rows JSON-safe.
- **Next:** As #59.

### #61 · 2026-10-11 · A5 · Per-agent collection quotas for the tournament
- **Done:** The 1.4x collection margin of #60 did not stop agent 2 of `runs/tourn-3` falling short: its deck's
  games record far fewer decisions, and workers stop on their shared total. `env/league_jobs.js` (used by
  the worker's `league` command): with `slotQuota`, a worker only draws matches whose recorded side's agent
  is below its quota and stops once every agent's quota is met (the total stays a hard cap); without it,
  unchanged. `env/runner.js` passes the recording to `nextJob`. `rl/tournament.py` sends quotas of 1.15x
  each agent's share per worker (`--quota-margin`) with a 3x hard cap (`--collect-cap`). tourn-3 keeps
  running on the old code (its workers loaded it); the rest of the chain moved to
  `runs/tournament_runs2.sh`, which waits for tourn-3, smoke-tests the quotas end to end (stops the chain
  if any agent is short), then runs tourn-6, tourn-9 and tourn-3-s2.
- **Evidence:** tourn-3 shortfalls under the margin: agent 2 at 7,635, 7,184 and 7,999 of 8,000 in three
  iterations (logged as `short_of_budget`). Simulation of the job picker (agent 2's games 7x shorter, 6
  games in flight): old rule 910 / 700 / 110 recorded against a 500 share; quotas 840 / 630 / 550.
- **Found:** tourn-3's per-agent budget is not exactly equal: the logged shortfalls are what to correct
  for when it is compared with the other runs.
- **Next:** As #59.

### #62 · 2026-10-11 · A1 / A5 · A second free cycle (Dark Dragonair) fixed in the engine; a per-turn cap; chain restarted
- **Done:** `runs/tourn-3` slowed several-fold from round 10 (tournament 4 s to 41 s, drafting 35 s to ~340 s,
  collection 15 s to ~55 s an iteration). From round 11, 23-28 of the 96 greedy tournament games ran to the
  5,000-step cap (1,250-1,470 decisions a game on average); training (sampled) had 0-10 capped games an
  iteration from round 8. `notes/scripts/trace_loop.js` (now with `--greedy`) on the agents exported for the
  round-14 evaluation showed agent 0 cycling Dark Dragonair TR's Evolutionary Light with no pick, about
  2,470 times. The engine checked the Power's once-per-turn marker but never set it, and with no card chosen
  the Power still shuffles the deck, so the state never repeats and the env's no-op test (#14, #20, #58)
  cannot see it. Fork `3ee2238`: the marker is set on use, with a spec. An audit of every "Once during your
  turn" Power in the 2000 sets found no other one without it. `env/game.js`: a safety net for cycles the
  no-op tests miss, `MAX_TURN_STEPS` 250: once a player-turn has had that many decisions, its main-phase
  decisions offer only `pass`. The N=3 run (15 rounds) is kept as `runs/tourn-3-loopbug`; the chain was
  restarted clean (`runs/tournament_runs3.sh`: the per-agent quota smoke test, then tourn-3, 6, 9, 3-s2).
- **Evidence:** After the fix, 32 of 32 greedy games between the same agents end normally (at most 223
  decisions). Sets specs 693/693 (the new one fails on the old code); `test_env` 100 games PASS;
  `verify_enumerator` 200 games PASS; `bench_env` 66.7 games/s/core; 1,200 random games between full-pool
  decks with 0 errors, 0 step-capped games and the per-turn cap never reached; `trace_hash` over 300 seeded
  2000-field games unchanged (e332007...), so neither change alters an ordinary game.
- **Found:** A free cycle can hide behind randomness: an action that only shuffles changes the state every
  time. Greedy play finds such cycles more readily than sampled play (25% of greedy games against 0.5% of
  training games here). The per-turn cap ends a turn rather than the game, so a cycling agent gains no draw.
- **Next:** As #59.

### #63 · 2026-10-11 · A5 · Tournaments of 3, 6 and 9 agents: results (2000s result #2); Venomoth fixed
- **Done:** `runs/tournament_runs3.sh` ran tourn-3, tourn-6, tourn-9 (seed 1) and tourn-3-s2 (seed 2), 20
  rounds each, 02:49-13:43, with no failure. `notes/scripts/tournament_report.py` (per-run summary from
  the logs) and `notes/scripts/tournament_crossplay.py` (the 21 final agents in one round-robin, each deck
  piloted by its own agent and by pilot-v2). The 21 final decks were played against the 24 archived lists
  under pilot-v2. An analysis workflow (4 analysts by question, one skeptic per claim recomputing it from
  the logs: 40 claims, 34 held, most corrected or downgraded) checked the conclusions. Written up as
  `results/2000s-result-2/`. Fork `c1cca1d`: Venomoth JU's Shift now sets its once-per-turn marker and
  changes Venomoth's own type (it changed the Active Pokémon's), with a spec; found by the analysis.
- **Evidence:** Deck types = N in all 84 run-rounds, closest pair at least 34 cards. Equilibrium support,
  mean 1.38 / 1.00 / 2.10 / 1.76 (N=3 s1, s2, 6, 9); rounds without a pure equilibrium 4 / 0 / 12 / 6;
  cyclic share of triads 0.19 / 0.00 / 0.10 / 0.05; genuine intransitivity only at N=6, rounds 0-10.
  Adoptions 0.42-0.45 per agent-round in every run. Own deck against SimpleBot at round 19: 0.88 / 0.81 /
  0.77 / 0.72 (slope p about 0.11), uncorrelated with cross-play strength (r = -0.06). Cross-play against
  other runs, own / common pilot: 0.461 / 0.573, 0.591 / 0.591, 0.431 / 0.428, 0.532 / 0.478; deck about
  70% of the strength variance, pilot about 30%. Answer key: 0 of 8 archetypes at 50% overlap (best any
  deck ever 0.43), final equilibria play 0-2 of the 7 field staples (random starts 0-2); against the
  archived lists under pilot-v2, 20% (best deck 41.5%). Field Basic Pokémon rose from 0.04-0.11 to
  0.27-0.39 of the agents' Pokémon (base rate 0.09). Final decks: 29.0 Pokémon / 5.3 Trainers / 24.1 basic
  + 1.5 special Energy (archived lists 13.9 / 27.5 / 14.6 / 4.0); 31.6% of Pokémon copies are evolutions
  without their pre-evolution in the deck. Every agent-iteration trained on exactly 8,000 transitions;
  0 errors; 0.16-0.26% of training games capped. Engine specs 694/694; `test_env`, `verify_enumerator`
  PASS; `trace_hash` unchanged.
- **Found:** (1) Owning a deck keeps agents apart at every N, but that is also what this drafting operator
  does by default. (2) The equilibrium stays at 1-2 decks, so its share of the field falls with N; no N
  effect on the meta's structure survives the N=3 seed spread, and N is confounded with data per opponent
  (fixed per-agent budget). (3) The swap operator draws added cards over card ids, 225 of 277 of them
  Pokémon, which by itself pushes decks toward Pokémon piles, and it adds evolutions without their
  lines; with pilots that get little from Trainers, the real-game test accepts these moves. (4) Own-deck
  play against SimpleBot is a reliable number that says nothing about strength in the tournament.
- **Next:** A drafting operator that proposes by card class and whole evolution lines and measures dead
  cards from the agent's own games, or a learned draft policy; the pilot's use of Trainers; more seeds at
  N=6 and 9 with a budget scaled by N-1.

### #64 · 2026-10-12 · A5 · Plan: the meta level cut to learned swap drafting + self-play; `pre-simplify` tag
- **Done:** Agreed with Evan a rewrite of the meta level to one procedure: N agents, each with its own
  pilot (TokenPointerNet, unchanged) and its own draft head, which samples one card swap (or "keep") per
  training game from cross-attention over the deck as encoded by the pilot; the pilot learns by PPO on
  win/loss plus potential-based prize shaping that fades to 0, the draft head by REINFORCE on the game
  result with a leave-one-out baseline; the deck advances by the head's mode once per iteration. The
  tournament, league, PSRO, value search, edit head and the analytics go (plan:
  `~/.claude/plans/i-want-to-you-unified-flask.md`). Before deleting anything: engine pin bumped
  `3d2a13e` → `c1cca1d` (commit `f3d9aa7`), tagged `pre-simplify`; fork `sts-2000-pool` pushed to
  `mine`, `main` and the tag pushed to origin.
- **Evidence:** `git ls-tree pre-simplify ryuu-play` gives `c1cca1d`; `git -C ryuu-play branch -r
  --contains c1cca1d` gives `mine/sts-2000-pool`.
- **Found:** Result #2's runs used engine `3ee2238`, which was neither pinned nor pushed until now; the tag
  pins `c1cca1d`, which adds only the Venomoth JU fix on top. Design review numbers: a one-copy change is
  worth about 1–2 points (#32 replaced every copy), so one game result per swap needs on the order of
  1,000 samples to resolve a 3-point effect for one choice; the head has to learn through the card
  embeddings (card type is in the features), not by trying every swap.
- **Next:** Prize shaping and the leave-one-out baseline in Python, with tests; recording in the worker's
  `games` command; `rl/draft.py`; `rl/metagame.py`; then the deletions.

### #65 · 2026-10-12 · A5 · The meta level rewritten: per-card learned drafting + self-play (`rl/metagame.py`)
- **Done:** Two changes to #64's plan from Evan: every card of the deck may change (not one swap at a
  time, which can stall in local minima), drawn at random, with the deck moving to a fresh draw each
  iteration; and the picks must use the game knowledge. New:
  - `rl/draft.py`: the agent's own pilot (frozen there; it learns only by PPO) reads the deck as a
    pre-game state (GLOBAL, 12 empty slots, MY_UNSEEN tokens with counts) against each deck of the field
    (the other agents' current decks), averaged; each candidate card is read inside the deck it would join.
    Per copy, replace with probability sigmoid(rate(H_j)) (about 3 cards a draw at the start); the
    incoming card from an identity-initialised cross-attention of H_j over the deck, scored against the
    candidates' in-context encodings plus a per-card bias. Copies are visited in random order with the
    masks updated after each replacement, so every draw is legal and its log-probability exact.
    REINFORCE with a leave-one-out baseline over the agent's games against the same opponent.
  - `rl/metagame.py`: N agents; every pair plays games-per-agent/(N−1) games an iteration, each side on
    a fresh draw; both seats recorded; PPO per agent (capped per iteration) with potential-based prize
    shaping that fades to 0 (`shape_rewards` in `rl/train.py`, applied to the rollouts before GAE; the
    prize bytes come from the worker's `info`, `env/tokens.js PRIZE_GLOB`); one REINFORCE step per head;
    each deck moves to one more draw.
  - `rl/evaluate_agents.py` (training never imports it): SimpleBot on each agent's own deck, the agents'
    round-robin with Nash and cyclic triads, every deck against the 24 archived lists under a common
    pilot, nearest archetype, staples.
  - The worker's `games` command records both seats when given `out` (`env/remote_worker.js`).
  Deleted (they reproduce from `pre-simplify`): rl/tournament, league, league_tests, psro, coevolve,
  search, builder, matchup, strength, deck_head, deckgen; env/league_jobs.js and the worker's `league`
  and `values` commands; `GpuMatrix.values`; `AgentView` and state capture in `rl/remote.py`;
  notes/scripts league_loops, matchup_ablation, deck_strength, trainer_restore_test (and pilot_diag's
  check that used it). Moved: `changed`, `deck_shape`, `random_deck` (the rules-only "flat" decks) to
  `rl/decks.py`; `subset` to `rl/rollouts.py`. `rl/tests.py` rewritten for what remains.
- **Evidence:** `rl.tests` PASS: random decks legal; 53,184 / 47,367 single-card swaps checked against
  `Pool.removable`/`addable` (field / full pool); subset; ONNX parity; shaping (λ = 0 identical, each
  trajectory telescopes to its result; on the 1,995 pilot-v2 rollout trajectories too, Φ = 0 at the first
  decision of all 1,995); RLOO; 500 draws legal with the batched log-prob within 8.5e-6 of the drawn
  one and 2.90 cards changed a draw; bandit, incoming mass on 8 target cards 0.029 → 0.952 in 200 steps.
  `test_env` 100 PASS, `verify_enumerator` 200 PASS (before and after the deletions). Recording smoke:
  20 games, 40 trajectories, 40 done flags, rewards ±1, 0 errors. Metagame smokes: pilot-v2, N=3, 48
  games per agent, 6 workers: 72 games an iteration in 6–8 s, about 11 s an iteration, 0 errors, 0 cut,
  legal decks, `--resume` continues from the saved iteration; random init, N=2: runs. `evaluate_agents`
  on `runs/tourn-3/checkpoint.pt`: against the archived lists 0.19 / 0.31 / 0.19 (result #2: 0.18 /
  0.26 / 0.17), round-robin within the ±0.09 per-entry noise of the run's own round-20 matrix.
- **Found:** Read without an opponent's list, the pilot's encoding of a deck is off its training
  distribution: cosine between the same card's token in the synthetic state and in real openings 0.36
  (another card of the deck: 0.27), 0.64 with an opponent's list added (the glob bytes do not matter),
  against 0.72 between two real openings of the same deck. Hence the reading against the field. A
  bandit that pays any hit taught the head to replace about 56 cards a draw: a result that grows with
  the number of changes drives the replacement rate up, so watch `expected_changes`.
  `Pool.removable` never removes the last Basic Pokémon, even for another Basic (the old builder masks
  allowed that swap); kept, since adding a Basic first gets there.
- **Next:** The development run from pilot-v2 (N=3, 400 games per agent, PPO capped at 8,000
  transitions, shaping 0.1 fading over 100 iterations), watching the replacement rate, the class mix,
  the draft KL and the correlation of changes with results; then `evaluate_agents` on its checkpoints.

### #66 · 2026-10-12 · A5 · Development run of the learned drafting: decks swing, two heads freeze; prize margin added
- **Done:** `runs/meta-dev`: `rl.metagame` from pilot-v2, 3 agents, 400 games per agent an iteration, PPO
  capped at 8,000 transitions per agent, prize shaping 0.1 fading over 100 iterations, 150 iterations.
  `rl.evaluate_agents` on the iteration-49 snapshot and the final checkpoint. Then, at Evan's choice, the
  draft heads' reward became result + `--draft-margin` (default 0.5) × the prize margin at the end
  ((opponent's prizes left − own) / 6): the worker's results now carry `prizesLeft` per seat
  (`env/runner.js`), and `rl/metagame.py` logs the mean margin per agent. Rerun started as
  `runs/meta-dev-c` with the same settings.
- **Evidence:** 90,000 games, 0 errors, 27 cut off, 17.8 s an iteration. Expected cards replaced a draw,
  start → end: a0 3.1 → 6.3 (max 6.7), a1 2.9 → 0.01 (under 0.5 from iteration 38, 112 of 150
  iterations), a2 2.9 → 0.08 (under 0.5 from 119). Mean result, first → last 10 iterations: a0 0.68 →
  0.16, a1 0.49 → 0.41, a2 0.33 → 0.94. Correlation of cards changed with result per iteration: mean 0.000 /
  −0.003 / −0.009. Draft KL per update, median 0.0019 / 0.0001 / 0.0011. In 73 agent-opponent iterations
  an agent won under 10% of its games against that opponent (a1 against a2 in 24, a0 against a2 in 19).
  Decks swung between extremes: a0 46 → 25 basic Energy by iteration 10, 9 Pokémon / 21 Trainers / 30
  Energy at 45, 22/14/24 winning 0.65 at 90, 50/4/6 winning 0.10 at 110, 3/53/4 at the end. Evaluation
  (SimpleBot on the own deck / archived lists under pilot-v2): iteration 49 0.52, 0.68, 0.62 / 0.04, 0.01,
  0.06; final 0.59, 0.75, 0.77 / 0.00, 0.02, 0.23 (result #2's tourn-3: about 0.88 / 0.20). At iteration
  49 a0's deck (5 Pokémon, 24 Trainers, 31 Energy) overlapped the Electabuzz / Mr. Mime archetype at 0.467,
  above any deck of result #2 (0.43), and played 6 of the 10 field staples; the final a0 plays 8 of 10 with
  3 Pokémon.
- **Found:** Two failure modes, both from one result per draw being too little evidence: (1) the head
  learns "change less" (one shared rate) much faster than "change to what" (~250 incoming cards), so a head
  whose random changes lose freezes, and frozen it never samples the swaps that would teach it; (2) the deck
  moves to a random draw whatever its games showed, so it can walk from a working deck into a pile. A
  frozen agent stays frozen while losing because the leave-one-out baseline only compares its games with
  its other games against the same opponent; and when it loses every game to an opponent, every draw gets
  the same result, so that matchup gives no gradient at all. The prize margin separates draws inside such a
  matchup. It never reverses a result at weight 0.5 (a win scores at least 0.5, a loss at most 0.5), but it
  ranks a prize win above a deck-out win, a mild game-specific preference (#51). In a 2-iteration smoke
  with it, an agent winning 71% (mostly by deck-out) had a mean margin of −0.31.
- **Next:** `runs/meta-dev-c` against this run. Still open if the freezing and the downhill walk persist:
  a fixed number of changes per draw (the head learns only which cards), and moving the deck only when a
  draw's games beat the current deck's.

### #67 · 2026-10-12 · A5 · The margin alone did not stop freezing; rewritten as a 99-deck population with one pilot, one draft head and turnover
- **Done:** `runs/meta-dev-c` (#66's settings plus the prize margin 0.5) stopped at iteration 84 of 150,
  all three heads frozen or nearly. At Evan's choice the loop became a population: `rl/metagame.py` now
  keeps --decks decks (99), one pilot and one draft head for all of them. Each iteration: every deck is
  read through the pilot against 4 other decks of the population; --games (2,000) games between random
  pairs, each side on a fresh draw of its deck; PPO on --record (500) of them (`games` jobs now carry
  `rec`, `env/remote_worker.js`); one REINFORCE step on every draw (result + margin, leave-one-out
  baseline over each deck's games); every deck moves to one more draw; every 10 iterations the worst 15%
  by results since the last turnover are replaced, 3 in 4 by a fresh rules-only random deck and 1 in 4
  by a deck of the best quarter with 10 cards replaced at random (`random_changes`). `rl/draft.py`: a
  draw now makes exactly --swaps (3) replacements, the copy going out chosen by a learned score
  (uniform over copies at the start), so there is no change rate to collapse; the deck's readings
  against its field sample run in one batch. `rl/evaluate_agents.py` takes a population checkpoint (one
  net) and scores its --top (12) decks by recent results. Started `runs/meta-99`: pilot-v2, 99 decks, 150
  iterations, shaping 0.1 fading over 100.
- **Evidence:** meta-dev-c, 51,000 games, 0 errors: expected changes fell under 0.5 at iteration 15 (a1;
  #66's run: 38), 40 (a0) and 43 (a2), ending at 0.76 / 0.00 / 0.00; mean result first → last 10
  iterations a0 0.72 → 0.88, a1 0.58 → 0.22, a2 0.20 → 0.39. `rl.tests` PASS with the new draws: 500
  draws legal with exactly 3 replacements each, batched log-prob within 2.6e-6 of the drawn one,
  `random_changes` legal, bandit target mass 0.029 → 1.000 in 200 steps. Population smoke (12 decks, 120
  games, 3 iterations, turnover every 2): 0 errors, about 6 s an iteration, 2 decks replaced at the
  turnover, `evaluate_agents --top 4` ran on its checkpoint.
- **Found:** In a1's freeze the result fell with the number of cards changed in 20–21 of the first 30
  iterations of either run (mean correlation −0.01 to −0.03), and Adam turned that weak, consistent push
  into a fall of the change rate from 3 to 0.01 in about 30 iterations; near 0 both the rate's gradient
  and the entropy bonus vanish with it, so the state cannot be left. The margin made a1's freeze come
  sooner (a1 was behind on prizes even while winning, mean margin −0.2 to −0.57).
- **Next:** `runs/meta-99`: whether decks keep improving with turnover feeding the population, how the
  class mix and the top decks move, and `evaluate_agents` on its snapshots against result #2.

### #68 · 2026-10-12 · A2 / A5 · The pilot sees every legal option; it ends 69% of turns holding a playable draw Trainer
- **Done:** At Evan's request ("it should obviously see every legal move"): the token encoder's bounds rose
  from 48 options and 128 state tokens to 128 and 256 (`env/tokens.js`), and a decision or state past
  them now ends the game as an engine error instead of being cut silently (`env/env.js`; the old code
  offered only the first 48 options). `TokenPointerNet` takes any number of candidates up to the bound,
  and the GPU server cuts each batch to its longest state and option list, so the bounds cost no compute
  there (`rl/remote.py`). `env/tools/evaluate.js --tokens` lets SimpleBot play decks with cards outside the
  archived field. `notes/scripts/trainer_diag.py` (evaluation only): Trainer usage in greedy games among a
  population's best decks, and a swap test (6 basic Energy → Bill / Professor Oak / Computer Search up to
  the copy limit) under the population's pilot and under SimpleBot. `runs/meta-99` was paused at iteration
  87 for it (its checkpoint is written every iteration) and resumed with `--resume`.
- **Evidence:** Random-move games on the 99 decks of `runs/meta-99` at iteration 79: 39,419 decisions, at
  most 39 options, none over 48; 11 decisions (0.03%) over 128 tokens. `rl.tests` PASS, including a new
  check that cutting a batch to its longest state and option list changes no output; `test_env` 100 and
  `verify_enumerator` 200 PASS. Diagnostics on the iteration-87 population
  (`notes/data/eval/trainer_diag_meta99_it87.json`): in 600 greedy games among the 12 best decks, a Trainer
  was playable at 59,843 of 89,602 decisions and chosen at 14.6% of them (mean probability on Trainers
  0.166); instead the pilot attacked 18,991 times and attached 16,768 times. 20,389 of 29,723 turn ends
  (attack or pass) came with a playable Bill, Professor Oak or Computer Search in hand; Bill was played
  1,570 times and a turn ended with it playable 12,317 times (Oak 845 / 11,141, Computer Search 480 /
  7,567). The best decks already ran 2–4 Bill, 2–3 Oak and 0–3 Computer Search, so the swap added 2–6
  cards (mean 4.3). Swap against the other 5 best decks: pilot 0.501 → 0.427 (64 games a pair), SimpleBot
  0.475 → 0.385 (200 games a deck).
- **Found:** (1) The pilot does not use its draw engine: it attacks, which ends the turn, before drawing.
  (2) Even so, the Energy the population converged on is not only a pilot artifact: trading about 4 basic
  Energy for draw Trainers hurt these decks under SimpleBot too, so in this field (Energy-hungry Colorless
  attackers, Energy Removal in 92 of 99 decks) the Energy does real work.
- **Next:** The pilot's turn order first (it attacks before drawing): find whether it is the representation
  of Trainer effects, the credit for a draw that pays off later in the same turn, or both; then
  `runs/meta-99` to its end and `evaluate_agents` on its snapshots.

### #69 · 2026-10-12 · A5 · 99-deck population: its best decks break even with the archived field under pilot-v2; drawing first is worth little in its meta
- **Done:** `runs/meta-99` ran its 150 iterations (paused at 87 for #68, resumed). `rl.evaluate_agents` on
  the snapshots at iterations 49 and 99 and on the final checkpoint (best 12 decks by recent results; the
  archived panel under pilot-v2 on both sides; SimpleBot 100 games a deck). `notes/scripts/draw_first.py`
  (evaluation only): the final pilot against itself on the 12 best decks, one side with a hand-written
  rule on top that plays any playable Bill (or Bill, Professor Oak and Computer Search) first.
- **Evidence:** 300,000 games, 2 engine errors, 2,012 cut off (0.67%). Population median Pokémon /
  Trainers / Energy at iterations 0, 20, 40, 60, 100, 120, 149: 21/15/19, 39/7/13, 19/22/17, 20/12/27,
  14/13/33, 20/5/34, 22/5/32. Evaluation (iteration 49 / 99 / 149): against the 24 archived lists under
  pilot-v2, mean 0.279 / 0.427 / 0.522, best deck 0.469 / 0.565 / 0.635 (result #2: 0.20, best 0.415); own
  pilot against SimpleBot on its own deck 0.627 / 0.741 / 0.864; closest archetype overlap 0.417 / 0.467 /
  0.450, all Wigglytuff (result #2: 0.43); field staples per deck 2.8 / 2.9 / 3.2 of 10; the 12 decks'
  equilibrium has 1 / 1 / 2 decks in support, with 8 / 16 / 17 of 220 triads cyclic. Draw-first against the
  plain pilot, 2,304 greedy games each: Bill first 0.513 ± 0.020; Bill, Oak and Computer Search first 0.418
  ± 0.020, with deck-outs 469 against 153.
- **Found:** (1) From random decks on the full pool, with nothing human in training, the population's best
  decks are even with the human field when one pilot plays both, which no earlier run came near. The
  panel's pilot (pilot-v2) shares this pilot's habit of not playing draw Trainers, which favours
  Trainer-light decks (the archived lists average 27.5 Trainers; the final population 5), so the number
  overstates how these decks would do against the human lists in a stronger player's hands. (2) Playing
  draw Trainers first gains at most about a point (Bill) and loses 8 points when Professor Oak and Computer
  Search are forced too, with three times the deck-outs: in this population's slow Energy and Energy
  Removal meta, extra draws bring a deck-out closer. Read with #68's swap test, the pilot's restraint with
  draw Trainers is largely right for the meta it built; the human meta was faster. (3) Trainers peaked at
  a median of 22 at iteration 40 and fell to 5 by 120, as the meta slowed.
- **Next:** An evaluation that does not share the pilot's style: the archived panel under a different or
  stronger pilot (the final pilot, SimpleBot on both sides). Then whether the meta's speed is set by the
  pilot (a pilot that plays for faster wins would favour draw engines), and the headline run from scratch.

### #70 · 2026-10-12 · A4 · Pilot ablations: switches, fixed decks and an 11-run chain, launched
- **Done:** At Evan's request ("do some ablations on the pilot architecture and training procedure").
  `TokenPointerNet` takes `card_inputs` (`all`: card features + rules text + learned residual, as before;
  `feats`: no text; `ids`: the learned per-card embedding alone, then started at N(0, 0.02) instead of 0)
  and `deck_tokens` (False masks the decklist tokens, own unseen cards and the opponent's list, out of
  attention); `rl.train` gets `--card-inputs`, `--no-deck-tokens`, `--shaping` / `--shaping-iters` (the
  potential-based prize shaping of #65, fading) and `--pace` (default 0.25, as `rl.metagame`; it was 0 in
  `rl.train`), and `rl.gpu_matrix.load_policy` reads the new keys (old checkpoints load as `all` / True).
  `notes/scripts/pilot_ablation.py`: `decks` takes every distinct deck of `runs/meta-99`'s population
  snapshots (594: random, evolved and mutant, drafted without human input), holds out lineages with
  population id % 5 == 0 (477 training, 117 held out) and writes 2,048 random training pairs
  (`runs/abl/matchups.json`); `eval` (evaluation only) plays a ladder of every variant's last snapshot and
  two anchors (pilot-v2 it349, meta-99's final pilot) on held-out decks with Bradley-Terry Elo (pilot-v2 =
  0), every snapshot against pilot-v2 (learning curve), each last snapshot against SimpleBot on the
  archived lists (480 games, seed 78 as #49) and on the held-out decks, and play style from the training
  log. `runs/pilot_ablation_run.sh` (started 21:50): 11 runs from scratch, 80 iterations each (~110k
  transitions an iteration), self-play, deck-out wins 1, lr 3e-4, pilot-v2's shape and PPO settings, one
  change each: base and base-s2 (seeds 1 and 2), no-decklists, ids-only, no-text, shaping (0.5 fading over
  the run), then no-count, small (d 192, 3 layers, 4 heads), league (past snapshots, as pilot-v2),
  gae1 (GAE lambda 1), deckout0 (deck-out wins 0; game-specific shaping, a diagnostic only); an
  evaluation after the first six and after all.
- **Evidence:** `rl.tests` PASS, with a new check: the `feats` / `ids` / hidden-decklist variants export to
  ONNX with matching outputs, have only the card input layers they should, and with hidden decklists
  changing 141 decklist tokens' cards and counts changes no output. Baseline smoke, 3 iterations: 111k
  transitions, 751 games and ~53 s an iteration (collect 10.5 s, PPO 42-45 s), GPU 63-70%. The `eval`
  script ran end to end on a 2-iteration toy run. No ablation result yet.
- **Found:** At random initialisation 89% of games end by deck-out (toy run), so early training is mostly
  about ending games at all.
- **Next:** The results (#71): which inputs and procedure choices matter at an equal budget, against the
  seed noise between base and base-s2, and which the headline run from scratch should keep.

### #71 · 2026-10-12 · A4 · From ablations to architecture improvements: slot binding and ability text, screen launched
- **Done:** At Evan's suggestion (iterative architecture improvements, "where does it make sense to add
  cross or self attention") the ablation chain of #70 was stopped after its second run: `base` finished
  (80 iterations, 64 min), `base-s2` runs on as the seed-noise floor, the other nine ablations did not
  start. Two new pilot options, off by default (old checkpoints load unchanged): `slot_bind`
  (`--slot-bind`): every token gets an embedding of the board slot it belongs to (`owner_and_count`: a
  SLOT token its own slot, UNDER / TOOL the slot in their aux, ENERGY slot = aux // 8), attached Energy
  gets its copy count (aux % 8) for the count features, and each encoder layer a learned per-head
  attention bias between tokens of the same slot, starting at 0 (`attend` takes an additive bias, also in
  the ONNX path); `ability_text` (`--ability-text`): an attack or Power option adds a projection of that
  ability's own rules-text embedding, looked up by the option's card and name id (`rl/card_text.py
  --abilities` → `notes/data/cards/ability_text.npz`, 417 abilities, 287 names, MiniLM as the card text).
  `runs/arch_iter_run.sh` screens three changes, each alone against base at #70's settings: slot-bind,
  cand-self (the existing option: the options attend to each other, 1 block, from scratch this time),
  ability-text; then the ladder on held-out decks (200 deck pairs, 400 games per pair of pilots) and
  learning curves (`runs/abl/eval_arch1.json`).
- **Evidence:** `base`: deck-outs 92% of games at iteration 0, 7% by 24, 11% at 79; prize wins 0% → 56% →
  62%; mean decisions per game 218 → 164; entropy 1.63 → 1.18. `rl.tests` PASS, with new checks:
  `owner_and_count` on a hand-made row; the slot-binding model with a non-zero bias and the ability-text
  model export to ONNX with matching outputs; all 417 abilities look up their own text; the name ids
  match `env/tokens.js` (287, same order). Training step at micro-batch 512 (d 256, 4 layers, 130 tokens):
  0.107 s and 2.51 GB without slot binding, 0.143 s (+34%) and 3.14 GB with it. A 2-iteration smoke with
  all three options trains and reloads. No screen result yet.
- **Found:** (1) Why slot binding: an attached card's slot was carried only by its aux id through a 256-way
  embedding, and the count features read ENERGY's aux (slot × 8 + copies) as a count, so slot 5 with 2
  Energy looked like 42 copies; per-Pokémon Energy by type was represented only that way (the slot
  features hold the total Energy count, not its types). (2) Why ability text: an attack option's only
  ability-specific input was a learned embedding of its name, most of the 287 names rarely or never
  played over the full pool.
- **Next:** The screen's ladder against the base / base-s2 gap; stack the changes that win, confirm the
  stack with two seeds, then the next candidates (history of recent actions, a joint state-and-options
  encoder).

### #72 · 2026-10-13 · A4 · Deck-free board encoder with cross-attention to the deck; screen restarted at 40 iterations
- **Done:** The #71 screen stopped at 00:17 on 2026-10-13 during slot-bind iteration 13 of 80, when the PC was
  shut down for the night (Evan); cand-self, ability-text and its evaluation never started. At Evan's request
  ("make sure the input game state is a good representation regardless of the deck, and then combined with
  cross attention on deck to get the deck specific state"), `TokenPointerNet` gets `deck_mode` (`--deck-mode`,
  default `joint` = as before, old checkpoints load unchanged) and `deck_layers` (`--deck-layers`, default 1):
  `cross` runs the board encoder with the decklist tokens (MY_UNSEEN, OPP_DECKLIST) masked out of its keys, so
  its output is a deck-free state (`encode(board_only=True)` returns it), a separate deck encoder over the
  decklist tokens alone, then one block in which the board tokens cross-attend to the deck tokens; `interleave`
  cross-attends after every board layer instead (the state is then not deck-free). The deck stream's token 0
  is a learned null key, so a state without decklist tokens still has one. The options and the value read the
  fused board tokens and the deck tokens, as before. `rl.train`, `rl.gpu_matrix` and
  `notes/scripts/pilot_ablation.py` read the new keys; `pilot_ablation.py eval --at N` scores every run at its
  last snapshot from iteration N or before. `runs/arch_split_run.sh` (launched 08:52): slot-bind resumed to
  40 iterations (from 08:48), then deck-cross, deck-cross-sb (with slot binding), deck-inter and no-deck
  (`--no-deck-tokens`), 40 iterations each at #70's settings, the ladder and learning curves at it39 on
  held-out decks (`runs/abl/eval_split.json`, base and base-s2 at it39 as the noise floor), then #71's
  cand-self and ability-text at the same budget and the ladder again (`eval_split2.json`).
- **Evidence:** `rl.tests` PASS, with new checks: `cross`, `interleave` and `cross` + slot binding + 2 deck
  layers export to ONNX with matching outputs; with 171 decklist tokens' cards and counts changed, the
  `cross` board encoder's output is unchanged and the fused board tokens change; a state with no decklist
  tokens gives finite outputs. Parameters at d 256, 4 layers: base 3,236,354; slot-bind 3,239,714;
  deck-cross 4,291,330 (+33%); deck-cross-sb 4,294,690; deck-inter 5,874,178 (+82%); no-deck as base.
  The learning rate is constant in `rl.train`, so a 40-iteration run is comparable to base's it39 snapshot.
  No result yet.
- **Found:** (1) Until now the board and deck tokens shared one self-attention stack, so from the first
  layer on there was no deck-free state, and the draft head reads a deck through that same encoder (a blank
  board plus decklist tokens, `rl/draft.py`). (2) The decklist tokens are asymmetric: MY_UNSEEN is my list
  minus what is visible, OPP_DECKLIST the opponent's full list, so the model has to subtract the opponent's
  visible cards itself. (3) deck-inter carries 82% more parameters than base, so a gain from it is confounded
  with size (#48: doubling the pilot gave a few points at most).
- **Next:** The ladder at it39: whether the deck-free board encoder plus cross-attention matches or beats the
  joint encoder beyond the base / base-s2 gap, what the deck tokens are worth (no-deck), and whether slot
  binding adds to it; then the winners at 80 iterations and two seeds, and the draft head reading the deck
  encoder directly.

### #73 · 2026-10-13 · A4 · Screen at 40 iterations: no architecture beats the seed noise, hiding the decklists does not hurt, lambda = 1 far worse
- **Done:** `runs/arch_split_run.sh`, then `runs/arch_split_run2.sh` and `runs/arch_split_run3.sh` (the chain was
  replaced twice: deck-inter ran out of GPU memory under the 0.8 cap at micro-batch 1024 and resumed at 512,
  the same gradient accumulated in half-size chunks; then, at Evan's choice, gae1 was put before the
  evaluation): slot-bind (resumed from it13), deck-cross, deck-cross-sb, deck-inter (resumed from it3),
  no-deck and gae1 (`--lam 1.0`: with gamma 1, each decision's advantage is the game's result minus its
  value), 40 iterations each at #70's settings, seed 1. `pilot_ablation.py eval --at 39 --parts ladder curve
  style --deck-pairs 200` (`runs/abl/eval_split.json`): the it39 snapshots of those six, base and base-s2, and
  the anchors pilot-v2 it349 and meta-99's final pilot, on held-out decks.
- **Evidence:** Ladder, 18,000 greedy games (400 per pair of pilots, 200 held-out deck pairs), 0 errors, 64
  cut by the turn cap, 231 s. Elo (pilot-v2 = 0, standard error 8; gae1 10): no-deck +18.1, slot-bind +12.6,
  base-s2 −0.6, deck-cross −3.6, base −7.1, deck-inter −15.0, deck-cross-sb −21.5, gae1 −308.7; meta-99 +128.1.
  Head to head (± 95%): base vs base-s2 0.475 ± 0.049; no-deck vs base 0.551, vs base-s2 0.519; slot-bind vs
  base 0.505, vs base-s2 0.521; deck-cross vs base 0.490, vs no-deck 0.471; deck-cross-sb vs slot-bind 0.443;
  deck-inter vs base 0.514; gae1 vs base 0.134 ± 0.033. Against pilot-v2 at it19 / it39: base 0.354 / 0.482,
  base-s2 0.344 / 0.529, slot-bind 0.232 / 0.526, deck-cross 0.203 / 0.503, deck-cross-sb 0.240 / 0.495,
  deck-inter 0.250 / 0.526, no-deck 0.438 / 0.557, gae1 0.130 / 0.175. Training logs, last 10 of 40 iterations:
  gae1 ends 60.5% of games by deck-out (base 5.2%, base-s2 12.2%), 13.7% by prizes (base 57.2%), 186 decisions
  a game (base 126), entropy 1.49 (base 1.08), value loss 0.75 against Monte Carlo targets (base 0.10 against
  lambda-returns, not comparable). Seconds an iteration: base 49, no-deck 49, slot-bind 62, deck-cross 65,
  deck-cross-sb 79, deck-inter 86 (micro-batch 512), gae1 53. `env/runner.js` plays every game of a
  collection to its end, so lambda = 1 never bootstraps a cut game as a draw.
- **Found:** (1) At 40 iterations with one seed, no architecture change separates from base: every
  head-to-head is within 5 points of even, and base and base-s2 differ by 2.5. (2) Hiding the decklist tokens
  (no-deck) does at least as well as every variant that reads them, and it leads at it19 (0.438 against
  pilot-v2, the others 0.20–0.35): on held-out decks the pilots do not yet gain from the decklists, so what
  carries play at this budget is the deck-free board. Whether the decklists are unused or fitted to the
  training decks is not yet known. (3) The deck-free board encoder with cross-attention (deck-cross) plays like
  the joint encoder (0.490 against base), so the split costs nothing measurable; slot binding with it was
  0.443 against slot binding alone, within two standard errors. (4) Lambda = 1 learns much more slowly: at it39
  it still loses most games by deck-out, as base did around iteration 10, because a Monte Carlo return over
  ~190 decisions carries the whole game's luck into every decision's advantage. Longer credit by this route
  costs more in variance than it gains at this budget.
- **Next:** Whether the decklists overfit the training decks (the same ladder on training decks against
  held-out ones); if so, decklist dropout in training so the board stream stands alone. More seeds or longer
  runs for the leading arms (no-deck, slot-bind), since one seed at 40 iterations only shows gaps above
  ~5 points. Lambda between 0.95 and 1 or per turn only if credit assignment comes back as the suspect.

### #74 · 2026-10-13 · A4 · Rest of the screen: cand-self and ability-text within noise; the ladder's own rerun noise; 40-iteration pilots weak on the archived lists
- **Done:** `runs/arch_split_run3.sh` finished at 14:35: SimpleBot for base, base-s2 and gae1
  (`runs/abl/eval_split_sb.json`), cand-self (`--cand-self 1`) and ability-text (`--ability-text`), 40 iterations
  each, seed 1, then the ladder, curves and style again with all ten arms (`runs/abl/eval_split2.json`). At
  17:42 SimpleBot for the other seven arms was started (same file).
- **Evidence:** SimpleBot, it39 snapshots, archived lists (480 games, seed 78) / held-out decks (480, seed 79):
  base 0.301 / 0.510, base-s2 0.344 / 0.550, gae1 0.085 / 0.139; anchors pilot-v2 it349 0.817 / 0.565 (#49:
  0.817), meta-99 final 0.724 / 0.777 (± 0.025–0.045). Second ladder, 22,000 games (400 per pair), 0 errors,
  85 cut: Elo slot-bind +19.5, no-deck +16.9, cand-self +15.3, base-s2 +14.2, base −5.3, ability-text −7.2,
  deck-inter −12.9, deck-cross-sb −13.2, deck-cross −14.2, gae1 −310.5 (± 7.3; gae1 9.1); meta-99 +128.1.
  Head to head (± 0.049): base vs base-s2 0.486; slot-bind vs base 0.583, vs base-s2 0.511; no-deck vs base
  0.519, vs base-s2 0.522; cand-self vs base 0.525, vs base-s2 0.520; ability-text vs base 0.514, vs base-s2
  0.435; deck-cross vs base 0.470, vs no-deck 0.445. The same it39 snapshots moved between the two ladders
  (the deck pairs are sampled afresh when the set of pilots changes): base-s2 −0.6 → +14.2, deck-cross −3.6 →
  −14.2; against pilot-v2 (curve, 192 games), no-deck it19 0.438 → 0.302 and it39 0.557 → 0.464.
- **Found:** (1) Correction to #73: no-deck "leads at it19" was evaluation noise; in the second sample it is
  0.302, among the others (0.21–0.39). What stands from both ladders is that hiding the decklists did not hurt.
  (2) The ladder's own rerun noise (about ±15 Elo for the same snapshots) and the seed noise (base against
  base-s2: 6.5 and 19.5 Elo) are as large as every architecture effect; only slot-bind against base (0.583)
  clears a 95% interval, and not against base-s2. A screen at one seed and 40 iterations cannot rank these
  changes; it needs several seeds, longer runs and the same deck pairs in every ladder. (3) On the 24
  archived lists the 40-iteration pilots win 30–34% against SimpleBot, against 51–55% on held-out population
  decks; pilot-v2 wins 82% / 56% and meta-99's pilot, trained 150 iterations on these population decks, 72% /
  78%. Play on the drafted decks is learned well before play on the human decks (27.5 Trainers on average,
  the population's 5), so the archived lists are the sharper test of a deck-agnostic pilot.
- **Next:** SimpleBot on the archived lists for every arm (running). Then fewer arms with more evidence:
  fixed deck pairs for every ladder, 2–3 seeds, longer runs, and the archived lists as the out-of-distribution
  measure; the decklist overfitting check and decklist dropout.

### #75 · 2026-10-14 · A4 · How far back the training signal reaches: a ground-truth credit probe; the value head is the weak link
- **Done:** (1) `runs/arch_split_run3.sh`'s last step finished at 18:12 on 2026-10-13: SimpleBot for the other seven
  arms of #73–74 (`runs/abl/eval_split_sb.json`). (2) At Evan's question ("I think the gradient signal is not reaching
  back? Can you also measure this"): the pilot has no memory, so no gradient flows through time; credit reaches an
  earlier decision only through the PPO advantage, GAE(lambda = 0.95) over one player's decisions with gamma 1,
  bridged by the value head. A probe measures that route against ground truth, evaluation only: `env/runner.js` jobs
  can start from a copy of a game (`fromGame`, `first`) and an `onDecision` hook sees every asked decision;
  `env/remote_worker.js qprobe` plays recorded self-play games with a pilot (sampled), copies the game at sampled
  main-phase decisions (no prompt open, two or more options; `--redeal` re-deals what the decider can't see) and
  plays each option to the end R times (the pilot sampling in both seats), recording each line's result and the
  advantage training would give the probed decision on that line, GAE(lambda) for eight lambdas from the decision's
  own value. `notes/scripts/credit_diag.py` reads it: Q^pi per option; per decision the *credit share* (covariance,
  across its options, of the expected training signal on one half of the lines with Q on the other half, over the
  same for the Monte Carlo signal lambda = 1, which is 1 by construction), the *alignment* (the correlation of the
  expected signal with Q across the options: 1 = right direction, only scaled), the signal-to-noise ratio of one
  game's signal, a split-half policy improvement gap, and the value's explained variance against the result by
  decisions to the end. Run on the training decks (1,120 games each) for base it79 and meta-99's final pilot
  (`runs/credit_run.sh`, `runs/credit/*.json`). `rl/gpu_matrix.load_policy` also reads rl.metagame checkpoints.
- **Evidence:** SimpleBot at it39, archived lists / held-out decks (480 games each, ± 0.040–0.045): no-deck 0.376 /
  0.592, slot-bind 0.335 / 0.559, deck-cross-sb 0.320 / 0.524, ability-text 0.319 / 0.541, deck-inter 0.304 / 0.530,
  deck-cross 0.278 / 0.555, cand-self 0.269 / 0.609 (#74: base 0.301 / 0.510, base-s2 0.344 / 0.550). Probe, first
  version (base it79, 12 lines and up to 6 options per probe, 4,070 probes, 236,496 lines, 0 errors, 37 min): the
  per-decision correlation of one game's advantage with the true advantage was too noisy to read (A*'s split-half
  reliability 0.05–0.42; corrected correlations −0.17 to 0.43 with no pattern), which led to the expected-signal
  measure. Second version, 16 lines and up to 4 options: base it79 4,082 probes, 237,408 lines, 0 errors, 29 min;
  meta-99 4,099 probes, 241,872 lines, 0 errors, 32 min. Value explained variance against the result (base) by the
  player's decisions to the end: 0–4 0.88, 5–9 0.83, 10–19 0.77, 20–39 0.63, 40–79 0.38, 80+ 0.15 (all 0.58; meta-99
  0.545). Spread of option values sd(dQ) 0.10–0.19 in every bin. By game turn 1–2 / 3–4 / 5–6 / 7–9 / 10–14 / 15+,
  base: credit share at lambda 0 (one-step TD) 0.24 / 0.16 / 0.32 / 0.36 / 0.29 / 0.20, at 0.95 0.63 / 0.65 / 0.75 /
  0.75 / 0.58 / 0.61; alignment at 0 0.32 / 0.28 / 0.50 / 0.54 / 0.45 / 0.34, at 0.95 0.87 / 0.90 / 0.95 / 0.95 /
  0.83 / 0.86; signal-to-noise of one game at 0.95 0.14–0.29, at 0 0.24–1.11, at 1 0.03–0.05. meta-99: share at 0
  0.14 / 0.33 / 0.26 / 0.34 / 0.34 / 0.34, at 0.95 0.56 / 0.74 / 0.59 / 0.67 / 0.74 / 0.71; alignment at 0 0.19 /
  0.43 / 0.40 / 0.45 / 0.45 / 0.48, at 0.95 0.86 / 0.89 / 0.85 / 0.84 / 0.88 / 0.90. Split-half improvement gap
  0.00–0.03 everywhere (a lower bound: one half's argmax is mostly noise at 8 lines).
- **Found:** (1) The signal does reach back, by a long return rather than by the value head: at lambda 0.95 the
  expected training signal carries 56–75% of an option's true effect and ranks options nearly right (alignment
  0.83–0.95), with early turns no worse than late ones. (2) The value head is the weak link: the change in value
  over one decision carries only 14–36% of an option's effect and ranks the options poorly (alignment 0.19–0.54), so
  credit has to come from about 20 decisions ahead, and one game's signal is then mostly that game's luck (noise
  variance 3–7 times the signal's). Training meta-99's pilot about twice as long did not improve this. (3) So the
  learning per game is limited by the value head: one that registered each move's effect would let a short lambda
  carry a well-aimed, low-noise signal, the route to a pilot that keeps improving with more games. Share and
  alignment at lambda 0 are a luck-free measure of that, cheaper than a ladder and comparable across arms.
- **Next:** Whether the weakness is the shared trunk and PPO's value training or the architecture: a copy of base's
  network refit on the value alone (and the value MLP alone on the frozen trunk), probed under base's own policy
  (`notes/scripts/value_refit.py`, `credit_diag.py --value-pilot`, running). Then the memory screen (#76).

### #76 · 2026-10-14 · A4 · Memory for the pilot: action history, a GRU and an attention memory; screen queued
- **Done:** At Evan's question ("Did you try any ablations for memory?"; none had been tried, the pilot sees only the
  current state). Three ways to see the past, each off by default (old checkpoints load and play unchanged):
  (a) *history tokens*: `env/game.js` records every step (who, turn, prompt or not, verb, the card it names; engine
  actions too, for SimpleBot's seat) and `env/tokens.js` with `history = W` adds the last W turns, newest first, at
  most 32, as HIST_ME / HIST_OPP tokens (aux = verb x 8 + turns ago; the opponent's prompt answers without their
  card, which may be hidden); `TokenPointerNet(history=W)` reads them with their own verb and age embeddings, other
  models mask them out. (b) *memory* `gru` / `attn`: after the encoder, a GRU, or one causal attention block with a
  turn embedding, over the player's own decisions in the game, fed the pooled state and added back to it through a
  zero-initialised projection; `forward(mem_lens=...)` runs whole trajectories (training), `forward(mem_states=...)`
  one decision with the state carried. Workers tag each request row with its game and seat and send finished games'
  ids (`env/remote_worker.js`); `rl/remote.py` keeps each seat's state between its decisions; `rl.train --memory`
  makes every PPO minibatch and micro-batch whole trajectories, so the backward pass runs through the game. No ONNX
  export for memory pilots: SimpleBot plays them through the inference server (`games` jobs with `bot`,
  `pilot_ablation.simplebot_gpu`). `rl.train --history`, the loaders and `env/tools/evaluate.js --history` pass W.
  `TokenPointerNet.heads` split out of `forward`. `notes/scripts/memory_reach.py`: the gradient of log pi + v at a
  decision with respect to the memory input k decisions earlier, as a share of its norm at the decision itself, and
  how much the policy and value change with the memory cut to the current decision. `runs/memory_run.sh` (after the
  value refit, `runs/vrefit_run.sh`): hist4, mem-gru, mem-attn, seeds 1 and 2, 80 iterations at base's settings,
  memory_reach after each memory run, then the ladder (fixed held-out deck pairs), curves, SimpleBot and style at
  it79 against base and base-s2 (`eval_mem.json`).
- **Evidence:** `rl.tests` PASS with new checks: history models export to ONNX with matching outputs; without the
  option 113 changed history tokens change no output, with it they do; for gru and attn a trajectory run whole gives
  the outputs of the same decisions played one at a time (logits within 1e-4), and the loss at a trajectory's last
  decision has a gradient at its first decision and none in other trajectories. `env/tools/test_env.js` PASS (200
  games). 20 random games with history 4: 16.4 history tokens per decision, at most 129 tokens. Smoke training, 2
  iterations each with history 4: gru and attn train and play; one PPO epoch over 20,099 rows alone on the GPU:
  2.83 s without memory, 3.75 s gru, 3.70 s attn. A 96-game ladder with both smoke pilots and the anchors, and
  SimpleBot through the server, 0 errors. memory_reach on the untrained smoke pilots: gru gradient share at lag 1 /
  2 / 4 / 8 / 16 / 32: 0.52 / 0.30 / 0.11 / 0.02 / 0.001 / 0.0; attn 0.017 at lag 1 to 0.0075 at lag 64.
- **Found:** (1) A player makes 70–100 decisions a game, and an untrained GRU's gradient is gone after about 16 of
  them (one or two turns): a GRU memory has to learn to hold its state before it can carry anything across turns,
  while the attention memory reaches every earlier decision in one step. (2) A benchmark run without the load
  limiter filled the GPU (15.8 GB, 100%) while the probe ran and slowed to a crawl; stopped within minutes. Every
  script here calls `limits.apply`.
- **Next:** The screen's results: whether any memory beats base / base-s2 beyond seed noise, how far each memory's
  gradient reaches after training and how much its play uses it, then the credit probe on the winner.

### #77 · 2026-10-15 · A4 · Value refit: more value fitting does not help; the value reads the state by cross-attention; chain restarted
- **Done:** (1) #75's value refit (`runs/vrefit_run.sh`, `notes/scripts/value_refit.py`): base it79's policy held
  fixed, 6 collections of self-play on the training matchups (622,456 decisions, about 5,200 games; 559,086 train /
  63,370 held out by game), then a copy of the whole network fit on the result alone (`base79-full`), and the value
  MLP alone on the frozen trunk (`base79-head`), 4 epochs each, keeping the epoch with the best held-out explained
  variance; then the credit probe of #75 with the refit value (`credit_diag.py --value-pilot`). Also from #75's data:
  the credit terms split by options the pilot plays (pi >= 0.1) and ones it rarely plays (`credit_diag.py --options`,
  `runs/credit/base79_likely.json`, `base79_unlikely.json`). (2) At Evan's direction ("Try cross attention for the
  value head"), two value readouts in `rl/token_model.py`, each off by default: `value_query = N`, N learned queries
  (each plus the pooled state) cross-attend to every encoder token through their own block and the value MLP reads
  their mean, the block starting as the identity so a checkpoint without it keeps its value; `value_tower = N`, the
  value's own N transformer blocks over the shared embedded tokens (joint deck mode only; not in any run yet).
  `rl.train --value-query / --value-tower`, the loaders (`rl/gpu_matrix.py`, `pilot_ablation.py`), `--init-from`
  leaving the new value weights at the identity, and `value_refit.py --value-query` (a fresh readout fit on a frozen
  trunk). (3) `runs/value_query_run.sh`, run by `runs/memory_run.sh` before the memory screen: the readout fit on base
  it79's frozen trunk with its credit probe (`base79-headx`); at Evan's "Or maybe we should bootstrap from existing
  knowledge?", base-cont (base it79 continued unchanged) and vq4-cont (the same with `--value-query 4`), 40
  iterations, seed 1; vq4 and vq4-s2 from scratch, 80 iterations; the ladder and style at it79 / it39
  (`eval_vq.json`), and the credit probe on base-cont and vq4-cont at it39. (4) The chain stopped 40 minutes into
  base79-head's credit probe: the PC was put to sleep at 00:24 on 2026-10-15 (Kernel-Power 187: a user-mode process
  called SetSuspendState; not a crash; the AC idle-sleep timeout is off). base79-head's probe is skipped (its refit
  barely moved the value). Restarted at 23:51 on 2026-10-15, detached from the session (`runs/vq_mem_restart.sh`,
  output in `runs/vq_mem_chain.log`), from the value query steps, then the memory screen of #76 unchanged.
- **Evidence:** Held-out explained variance of the result (EV) before fitting: 0.588 (the network's own value;
  0.594 on the head run's collection). Whole network: train MSE 0.361 / 0.212 / 0.131 / 0.090 by epoch, held-out EV
  0.482 / 0.394 / 0.387 / 0.350, so no epoch was kept and the saved copy is base's own network. Value MLP alone: train
  MSE 0.424 / 0.409 / 0.395 / 0.381, held-out EV 0.600 / 0.599 / 0.595 / 0.589, epoch 0 kept (+0.006). The probe
  with base79-full's value (base's own, on new games; 4,117 probes, 239,760 lines, 0 errors, 54 min) against #75's
  probe of base (4,082 probes): credit share at lambda 0 0.288 [0.243, 0.340] vs 0.257 [0.206, 0.315], at 0.95 0.725
  [0.677, 0.778] vs 0.647 [0.601, 0.695]; alignment 0.40 vs 0.40 at 0 and 0.91 vs 0.89 at 0.95; by game turn the
  lambda-0 share moved by up to 0.23 (turns 3–4: 0.39 vs 0.16). Options split: rarely played options' lambda-0
  share by turn 0.15–0.34 (all options 0.16–0.36); played options' 0.02–1.21, unstable (few played options per
  decision). `rl.tests` PASS (40 s) with new checks: the policy ignores the value tower and the value
  cross-attention, the value reads them; both export to ONNX with matching outputs. Base it79 loads with a 4-query
  readout (527,616 new weights). Restart: base79-headx's refit running, GPU 51%, 3.8 GB. No training smoke run
  with `--value-query` before the chain.
- **Found:** (1) The value is not under-trained on its trunk: an MLP on the pooled token gains 0.006 EV however long
  it trains, and the whole network fit on results alone overfits from the first epoch (train MSE to 0.09 while
  held-out EV falls), since about 5,200 games give about 5,200 independent targets for 3.24M weights. So the weak
  one-step value of #75 is not fixed by more value fitting of the same readout on fixed data; what is left is the
  readout (whether the other tokens hold more than the pooled one) and the number of games, which bootstrapping from
  base raises. (2) The probe reproduces its overall share and alignment within their intervals on new games, but a
  single turn bin moves by up to 0.23, so arms should be compared on the overall numbers, not per bin. (3) The value
  is not worse on options the pilot rarely plays; the split is too noisy on played options to say more. (4) A chain stopped by
  the machine going down again (#72: shut down overnight; now sleep): the chains run for many hours.
- **Next:** The chain: base79-headx's EV and credit share (does reading every token help the value at all?),
  base-cont vs vq4-cont from the same start, vq4 vs base / base-s2 from scratch, then the memory screen. About
  15 hours (5–6 for the value steps, about 10 for the memory screen, #76) if the PC stays awake.

### #78 · 2026-10-16 · A4 · Value cross-attention on a frozen trunk is worse; the short screens cannot rank pilot changes, one long run proposed
- **Done:** The restarted chain's first step (#77, `runs/value_query_run.sh`): a fresh cross-attention value readout
  (4 queries) fit on base it79's frozen trunk (`value_refit.py --head-only --value-query 4`, tag `base79-headx`), on
  621,056 decisions (558,480 train / 62,576 held out by game). Its credit probe is running; since no epoch was kept,
  it measures base's own value again. A review of the pilot screens since #70 against pilot-v2's learning curve
  (#48). Stopping the probe and the chain from this session was refused by the session's permission mode, so the
  chain runs on.
- **Evidence:** Held-out explained variance of the result before fitting 0.590; by epoch 0.583 / 0.545 / 0.517 /
  0.478 with train MSE 0.404 / 0.351 / 0.301 / 0.264; no epoch kept (the MLP alone on the same trunk, #77: 0.600
  at epoch 0). pilot-v2 against SimpleBot on the archived decks (#48): it24 49.5%, it49 58.8, it99 55.9, it149
  77.0, it199 81.5, it299 83.3. The screens compared their arms at it39 (#73–74); the queued arms run 40–80
  iterations.
- **Found:** (1) Reading every token makes the value overfit sooner than the MLP on the pooled token: with #77,
  the value is limited by the number of games (about 5,200 here), not by how it reads a trained trunk. Whether a
  readout trained with the trunk from the start helps is what vq4-cont and vq4 would test. (2) About a dozen pilot
  changes since #70 (ten screen arms in #73–74, three value refits in #77–78) and none separated from base beyond
  noise. pilot-v2 gained most of its strength between iterations 99 and 199 (55.9% to 81.5%), and every
  comparison stopped at iteration 39–79, before that phase. pilot-v2 trained with other settings (a league,
  deck-out wins 0, #42's decks), so this suggests rather than shows that the screens stop too early; the queued
  15 hours (value readout, then the memory screen) have the same limit.
- **Next:** Proposed in place of the queue: one long run, base from it79 to about it300, with SimpleBot on the
  archived lists and the held-out decks every 25 iterations. If it reaches pilot-v2's ~80%, the training recipe is
  sound and the pilot screening ends; the headline run follows. If it plateaus well below, the recipe has a
  problem to find, in a run long enough to show it. Needs the chain stopped (from Evan's shell). Off the GPU
  meanwhile: the evaluation that does not share the pilot's style (#69).

### #79 · 2026-10-16 · A4 · The Trainer probe: draw Trainers pay only under good follow-through; training sees Trainer effects
- **Done:** (1) The chain of #77 was stopped at Evan's request at 00:22 on 2026-10-16, during base79-headx's
  credit probe (which measured base's own value, #78); base-cont, the value readout arms and the memory screen
  never started and are parked. The long run proposed in #78 is withdrawn: pilot-v2 (#48) already trained this
  long and plateaued near 83% against SimpleBot, so it would mostly re-measure that. A search of the log, notes
  and commits for earlier attempts found play-time search and expert iteration tried or designed before (#13
  flat Monte Carlo, #50 psearch, #51 design) and KataGo-style auxiliary value heads recommended in
  `notes/analysis-2026-10-06.md` but never built. (2) The Trainer probe (evaluation only), answering #68's open
  question (the representation of Trainer effects, or the credit for a draw that pays off later):
  `env/remote_worker.js` qprobe `focus` (a verb) probes only decisions that offer an option with that verb, and
  probes the option played, then every attack and pass, then the focus options, then the rest; `greedyLines`
  plays the probe's lines greedily. `notes/scripts/credit_diag.py`: `--panel archived` (the 24 lists),
  `--focus`, `--greedy-lines`, and a per-card table: the pilot's probability of playing the card when offered;
  dscore, its expected score minus the alternative's ((Q + 1) / 2, points) against the pilot's likeliest attack,
  against pass, and against the pilot's mix of its other probed options; seen, the expected training signal's
  difference over Q's; track, the same across probes by split halves; gain, playing the card where it looks better
  than the pilot's mix on one half of the lines, valued on the other (better timing's worth, free of selection
  noise). `runs/trainer_probe_run.sh` and `runs/trainer_probe_greedy.sh`: 1,000 games on random pairs of the
  archived lists, hidden cards re-dealt in every line, probe-p 0.05 (at most 8 a game), up to 6 options, 16 lines
  an option; pilot-v2 it349 with sampled lines, base it79 with sampled lines, pilot-v2 it349 with greedy lines.
- **Evidence:** pilot-v2 sampled: 4,249 probes, 348,832 lines, 1 line error, 34 min; base it79: 4,528 probes,
  372,272 lines, 9 line errors, 37 min; pilot-v2 greedy: 4,366 probes, 358,560 lines, 5 line errors, 35 min; 0
  game errors. Per card, pilot-v2 sampled / base sampled / pilot-v2 greedy: probability of playing when offered,
  Bill 0.14 / 0.11 / 0.15, Professor Oak 0.11 / 0.03 / 0.12, Computer Search 0.10 / 0.04 / 0.10, Energy Removal
  0.23 / 0.18 / 0.27, Gust of Wind 0.11 / 0.13 / 0.12; against the likeliest attack (points), Oak −10.2 / −11.7 /
  −10.6, Scoop Up −11.2 / −8.8 / −11.2, Bill −2.8 / −1.5 / −1.1, Computer Search −2.9 / −3.9 / −2.5. Gain from
  better timing (points per decision where offered, 95% interval): all Trainers +0.52 [0.25, 0.79] / +0.35 [0.14,
  0.59] / +0.97 [0.70, 1.25]; Bill +0.32 [−0.19, 0.79] / +0.12 [−0.40, 0.61] / +1.16 [0.50, 1.82]; Oak −0.27
  [−0.66, 0.14] / −0.06 [−0.34, 0.18] / +0.52 [0.06, 1.00]; Computer Search −0.37 / −0.70 [−1.04, −0.40] / +0.27
  [−0.28, 0.81]; Energy Removal +1.24 [0.39, 1.99] / +1.13 [0.31, 2.06] / +0.65 [−0.33, 1.50]; Gust +1.14 [0.58,
  1.68] / +0.29 [−0.29, 0.91] / +1.55 [0.95, 2.21]; PlusPower +0.62 [0.08, 1.21] / +0.67 [0.13, 1.17] / +1.08
  [0.48, 1.72]; Energy Retrieval +0.28 / +0.11 / +1.53 [0.40, 2.61]. Credit at these decisions (sampled runs), all
  options: share at lambda 0 0.41 [0.38, 0.45] (pilot-v2), 0.54 [0.51, 0.56] (base; #75, all decisions on its
  training decks: 0.26); at 0.95 0.76 / 0.78; alignment at 0 0.50 / 0.64, at 0.95 0.92 / 0.92. Against pass, seen
  at lambda 0.95 is 0.4–2.0 across cards (about 1 for Energy Removal, Gust and PlusPower); track at lambda 0
  against the pilot's mix −0.06 to 0.66. Value explained variance over all decisions on the archived lists 0.39
  (pilot-v2, trained with deck-out wins 0 and scored here on the full result) and 0.46 (base).
- **Found:** (1) Under sampled play, the play training learns from, playing draw Trainers more is worth nothing
  measurable for either pilot (Bill, Oak, Computer Search between −0.70 and +0.32), and the low rate at which they
  play them (#68–69) is mostly right on average: Oak and Scoop Up cost about 10 points against attacking. The
  value they leave is in Trainers that act on the opponent's board or the attack (Energy Removal, Super Energy
  Removal, Gust, PlusPower, Lass: +0.6 to +1.3). (2) When the rest of the game is played greedily, draw Trainers
  are worth timing better too (Bill +1.16, Oak +0.52, Energy Retrieval +1.53; all Trainers +0.97 against +0.52
  sampled). A draw only pays through the moves that follow it, and a sampled follow-through over the longer turn
  it creates spends that value, so on-policy training with this much entropy sees little reason to draw. (3) The
  training signal carries the average effect of Trainer plays, at one step about twice the share of an average
  decision (0.41–0.54 against 0.26), so the delay to a Trainer's payoff is not what blocks learning; what is weak is
  telling the situations apart (track up to 0.66, often near 0), and the sampled follow-through of (2). (4) The
  gains are per decision where the card is offered, at many decisions a game, so they are not additive into a win
  rate; not measured as a game-level effect.
- **Next:** Whether the sampled follow-through limits Trainer play in training: the greedy-lines probe on base
  it79, then a training arm that collects with less sampling noise (a lower temperature or entropy weight), judged
  on the archived lists and by this probe's timing gains. For telling situations apart, the auxiliary value heads
  of `notes/analysis-2026-10-06.md`. Then the evaluation that does not share the pilot's style (#69).

### #80 · 2026-10-16 · A4 · Greedy-lines Trainer probe on base it79: under good follow-through every Trainer is worth timing better
- **Done:** `runs/trainer_probe_greedy.sh` extended to base it79 (a pilot whose summary exists is skipped), the
  settings of #79: 1,000 games on the archived lists, hidden cards re-dealt, probe-p 0.05, up to 6 options, 16
  greedy lines an option. A check of the log and run scripts for earlier entropy or temperature changes to the
  pilot: every pilot run kept `--ent 0.01`; the only change was the tournament's rising entropy weight (#59–60).
- **Evidence:** 4,450 probes, 364,512 lines, 7 line errors, 0 game errors, 31 min; value explained variance over
  all decisions 0.48. Gain from better timing (points per decision where offered, 95% interval), greedy lines /
  #79's sampled lines: all Trainers +1.32 [0.99, 1.66] / +0.35; Professor Oak +1.36 [0.94, 1.78] / −0.06; Bill
  +0.74 [0.26, 1.25] / +0.12; Computer Search +0.60 [0.17, 1.05] / −0.70; Item Finder +0.84 [0.31, 1.45] / −0.03;
  Scoop Up +1.11 [0.49, 1.77] / −0.20; Energy Removal +1.30 [0.45, 2.23] / +1.13; Super Energy Removal +1.72 [0.81,
  2.77] / +0.94; Gust of Wind +2.12 [1.33, 2.98] / +0.29; PlusPower +0.88 [0.15, 1.63] / +0.67; Energy Retrieval
  +2.48 [1.00, 4.26] / +0.11; Lass +1.86 [0.25, 3.60] / +0.97. Against the likeliest attack: Oak −10.0, Scoop Up
  −9.0, Bill −2.3. The probabilities of playing each card are base's own (Oak 0.037, Bill 0.116, Gust 0.131).
- **Found:** (1) For the current recipe, every Trainer above is worth timing better once the rest of the game is
  played greedily, the draw and search cards included, while under base's sampled play only the disruption cards
  are: base's own sampling after a Trainer erases most of what it is worth, so PPO, which scores a decision by the
  sampled play after it, gets little signal for when to play one. (2) The gap is larger for base than for
  pilot-v2 (+1.32 greedy against +0.35 sampled; pilot-v2 +0.97 against +0.52, #79): the weaker pilot times
  Trainers worse and wastes more of them in its follow-through, in line with its 30–34% against SimpleBot on these
  lists (#74). (3) A lower entropy weight or sampling temperature for the pilot has never been tried.
- **Next:** A training arm with less sampling noise in the play it learns from, against base and base-s2 from
  the same start: a lower entropy weight (or one annealed to 0), and collection at a temperature below 1 with the
  behaviour log-probabilities recorded; judged against SimpleBot on the archived lists and by whether the probe's
  sampled-line timing gains move toward the greedy ones. Then the auxiliary value heads.

### #81 · 2026-10-16 · A4 · Mostly greedy collection (--explore), and a chain that tests it against base
- **Done:** Commit `8ed948b` (#79–80's probe code and notes), pushed to origin main. Evan, on #80's proposal to cut
  the sampling noise: "it should be greedy then within the game. I just don't know how it will explore all of the
  combinations of play interactions then?" The answer is to explore at a few decisions and play greedily at the
  rest, as the probe does. `rl/train.py --explore e` (GPU inference only): each decision of a model seat samples
  from the policy with probability e and otherwise plays its top option (`rl/remote.py`, both seats and any league
  snapshot); each recorded decision says which (`sampled`, carried by `env/remote_worker.js`, `env/runner.js` and
  `rl/rollouts.py`). `ppo_update`: the policy terms (clipped objective, KL, clip fraction) and the advantage
  normalization use only the sampled decisions, because at a greedy one the recorded log-probability is not what the
  move was chosen with; the value loss and the entropy bonus use every decision; without `--explore` every decision
  is sampled and the update is the one before. The log gains `sampled`, the share of sampled decisions.
  `runs/explore_run.sh`, started detached 09:06 (`runs/explore_chain.log`): from base it79, 40 iterations, seed 1,
  base-cont (unchanged), explore-cont (`--explore 0.1`) and ent-cont (`--ent 0.001`); the ladder, SimpleBot and
  style on them (`eval_explore_cont.json`) and the greedy-lines Trainer probe of #80 on each at it39; then from
  scratch at base's settings, explore10 and explore10-s2 (80 iterations, seeds 1 and 2; base and base-s2 are the
  controls), and the ladder, curves, SimpleBot and style at it79 (`eval_explore.json`).
- **Evidence:** `rl.tests` PASS, with a new check: with a `sampled` mask, `ppo_update`'s policy loss, KL and clip
  fraction equal their closed forms over the sampled rows, all ones gives the unmasked stats, and micro-batches of
  64 give the same step as one batch of 256. Smoke run, 2 iterations from scratch, 4 workers: sampled share 0.0997
  and 0.1021, 0 errors, 0 cut games. base-cont, first 3 iterations: 48 s each (collection 10–12 s), entropy
  1.18–1.20, GPU 71–89%, 13.9 GB in use on the card.
- **Found:** With e = 0.1 the policy learns from a tenth of the decisions it did, so per iteration its gradient is
  noisier; a loss for explore-cont could come from that rather than from the greedy follow-through, which is why the
  entropy-weight arm and the from-scratch pair run beside it.
- **Next:** Read the chain: explore-cont and ent-cont against base-cont on the ladder and against SimpleBot on the
  archived lists, and whether the probe's timing gain falls (better timing) and p_play of the draw Trainers rises;
  then the from-scratch pair against base and base-s2.

### #82 · 2026-10-16 · A4 · Mostly greedy collection loses, and more ordinary training is what teaches Trainer timing
- **Done:** `runs/explore_run.sh` (#81) ran 09:06–15:41 with no failure: base-cont, explore-cont and ent-cont (40
  iterations from base it79), their ladder, SimpleBot and style (`runs/abl/eval_explore_cont.json`), the greedy-lines
  Trainer probe of #80 on each at it39 (`runs/credit/trainer-{base-cont,explore-cont,ent-cont}-39-greedy.json`), then
  explore10 and explore10-s2 from scratch (80 iterations) with the ladder, curves, SimpleBot and style at it79
  (`runs/abl/eval_explore.json`). Timing gains by #80's split-half analysis (a scratch script over `credit_diag.py`'s
  focus rows). `rl/train.py --policy-share p`: sampled play, but the policy trains on a random share p of the decisions
  (the control for --explore's thinner policy data); not run. Claude Code stopped this session's watcher at ~11:29 for
  low system memory (3.3 of 31.4 GB free with a game running); the chain was not affected.
- **Evidence:** Ladder on held-out deck pairs (Elo, pilot-v2 = 0, ± 4.8–4.9): base it79 80.5, base-s2 101.4,
  base-cont 135.4, ent-cont 139.7, explore-cont 19.4, meta-99 146.0 (33,600 games, 0 errors). Against SimpleBot,
  archived / held-out / random decks (± 0.036–0.049): base 0.418 / 0.686 / 0.510; base-cont 0.514 / 0.750 / 0.495;
  ent-cont 0.475 / 0.806 / 0.500; explore-cont 0.339 / 0.626 / 0.465. From scratch, ladder at it79 (± 5.1–5.2): base
  85.1, base-s2 106.2, explore10 28.4, explore10-s2 18.1; against pilot-v2 at it19 / 39 / 59 / 79: base 0.372 / 0.496 /
  0.561 / 0.616, base-s2 0.376 / 0.496 / 0.598 / 0.624, explore10 0.463 / 0.513 / 0.506 / 0.539, explore10-s2 0.403 /
  0.513 / 0.523 / 0.545; SimpleBot archived 0.359 / 0.319 (base 0.418, base-s2 0.444). explore-cont's KL per update
  stayed 0.035–0.07 and its gradient norm above the 0.5 clip all 40 iterations (base-cont 0.017–0.026, ~0.4).
  Trainer probe, all Trainers (gain from better timing, points per decision where offered, 95% interval; the pilot's
  probability of playing one when offered): base it79 +1.32 [0.99, 1.66], 0.225 (#80); base-cont +0.39 [0.12, 0.64],
  0.326; ent-cont +1.10 [0.82, 1.37], 0.212; explore-cont +1.87 [1.56, 2.24], 0.181. Oak +1.36 / +0.15 / +0.13 /
  +2.42 (played 0.037 / 0.104 / 0.078 / 0.049); Bill +0.74 / +0.49 / +0.71 / +0.69 (0.116 / 0.231 / 0.176 / 0.131);
  Gust +2.12 / +0.83 / +2.06 / +2.55. Probes 3,822 / 4,860 / 4,641; 1 / 19 / 9 line errors, 0 game errors; 32–44 min each.
- **Found:** (1) Mostly greedy collection at e = 0.1 is worse. From base it79 it ended 61 Elo below its own start
  and 116 below the unchanged continuation; from scratch it learns faster for 20 iterations and then falls behind
  (0.54 against pilot-v2 at it79, base 0.62), 6–13 points lower against SimpleBot on the archived lists. (2) The
  probe overturns #80's reading. base-cont, still sampling every decision, cut the room for better Trainer timing
  from +1.32 to +0.39 points and played Trainers more (0.225 → 0.326; Oak 0.037 → 0.104, Bill 0.116 → 0.231) in 40
  iterations, so sampled follow-through does not stop PPO from learning when to play a Trainer; base it79 had not
  yet learned it. Less exploration made it worse in both arms: the less a pilot sampled, the fewer Trainers it played
  and the worse it timed them. A likely reason, not verified: a Trainer the pilot rates low is rarely its top option,
  so at e = 0.1 it is tried at about a tenth as many decisions (Evan's worry about exploring the combinations); the
  thinner policy data may add to it, which `--policy-share` would separate. (3) The 80-iteration screens stop while
  base is still learning: 40 more iterations gave +55 Elo and +9.6 points against SimpleBot on the archived lists.
  #78 dropped a long run because pilot-v2 plateaued near 83% against SimpleBot; base is at 51%, well short of that.
- **Next:** Continue base-cont with ordinary sampled collection and `--ent 0.01` for about 160 more iterations, with
  the Trainer probe and SimpleBot on the archived lists every 40, to see where this recipe levels off relative to
  pilot-v2. The `--policy-share 0.1` control only if mostly greedy collection comes back as an idea.

### #83 · 2026-10-18 · A4 / A5 · The lab: the metagame loop as a main line that keeps training, changes tested as short branches
- **Done:** At Evan's request (a plan to test architectures and metagame setups autonomously without getting stuck in long
  runs, then "Do 1/3 GPU so I can use it but keep iterating. The constant though is that the method should generalize to
  other card games, and that the ground truth is rediscovering the meta through playing the decks that it drafted, reusing
  learnings from the game in the meta drafting"): `notes/plan-lab.md` and `rl/lab.py`. The main line is `rl.metagame`
  itself (one pilot trained only on drafted decks, a draft head reading decks through it), continued from meta-99's state
  after 150 iterations (#69), in segments of 10 iterations. A card (`runs/lab/cards/*.json`, written before its run) forks
  the main line's whole state at a segment boundary, changes one thing and runs the same segment(s); the control is the main
  line's own segment. Pilot cards: the branch's pilot against the main line's on fixed deck pairs drawn from both
  populations (both pilots on both decks, both seat orders, the same deals), a sequential probability ratio test of
  H0 Elo <= 0 against H1 Elo >= elo1 (15 until the A/A sets it), alpha = beta = 0.05, at most 1,500 pairs; gate: on the 24
  archived lists (276 pairs), not clearly worse (H0 Elo <= -elo1 against H1 Elo >= 0 not accepted); "test": "noninferior"
  for changes that save time. Two-segment cards stop early only if clearly worse. Meta cards: the answer key of both
  populations under the main line's pilot (`rl.evaluate_agents`, 16 games a pair) with a rule written into the card, the
  pilot test as a gate. A/A cards: every test at full length, no decision. Passed: adopted (the main line continues from
  the branch), one at a time; undecided: closed. Milestones every 40 iterations: `rl.evaluate_agents` with SimpleBot and
  pilot-v2 as the common pilot (as #69). The lab waits when free RAM < 6 GB or free GPU memory < 5 GB, holds off idle
  sleep, and a `runs/lab/STOP` file ends it after the current iteration; every step resumes from files. Supporting changes:
  `rl/limits.py` RL_GPU_SHARE (memory fraction, Pace's load, and the inference server's least rest of 1 / share - 1 in
  `rl/remote.py`) and RL_CPU_THREADS, unset = unchanged; `rl/train.py` `token_net` (a pilot from a checkpoint's whole
  config), `load_grown` (new modules; additive new inputs, slot binding's owner embedding and the ability projection,
  start at 0) and `remap_adam` (moments by parameter name); `rl/metagame.py` `--fork-from`, `--pilot-opts`, `--reseed`,
  `--freeze-pilot`, `--ent / --epochs / --micro-batch / --lam`, `--stop-file`, the deal seed kept in the checkpoint, the
  population size taken from the source; `rl/evaluate_agents.py` loads any architecture and takes a metagame checkpoint as
  `--common`. Launched detached at 22:52 with RL_GPU_SHARE 0.333 and RL_CPU_THREADS 10 (8 workers): cards 001-aa-same,
  002-aa-reseed (`--reseed 2`), 003-pilot-vq4 (`value_query 4`, two segments), 004-pilot-epochs2 (`--epochs 2`,
  noninferior).
- **Evidence:** `rl.tests` PASS, with `check_lab`: the test statistic equals the normal log-likelihood ratio computed directly
  (7.152); it drifts up under H1 (31.4 → 287.7 at 5,000 / 50,000 samples) and down under H0 (−39.5 → −289.6); Elo and score
  invert; bounds ±2.944; pair scores on a hand-made matrix; a pilot grown by value_query 2 and slot binding (19 new weights,
  the additive ones at 0), and with value_query alone policy logits within 1e-5 of the source's; remap_adam keeps every
  moment by name and gives the new parameters none; in a fresh interpreter RL_GPU_SHARE 0.333 / RL_CPU_THREADS 10 give a
  memory fraction 0.333, server and Pace rest 2.003, 8 workers, and unset 0.8 / 0 / 14. Smoke (`runs/lab-smoke`, 40 games an
  iteration, segments of 2, 4 workers, deleted after): two bugs found and fixed (an argument clash in `event`; a card started
  at m counted as behind, which re-ran a zero-iteration branch until the STOP file ended it within one step); then the main
  line 150 → 152 in 0.5 min, three forks in 0.4 min each, the A/A card measured (drafted panel 120 games +23.2 Elo
  [−29.8, 77.3]; archived 1,104 games +12.0 [−4.7, 28.7] in 235 s), the pilot card inconclusive at its 30-pair cap, the meta
  card passed an always-pass rule and was adopted (main checkpoint and seg_0152 replaced, the old one kept, lineage and
  `lab.json` updated), STOP ended it after the segment in progress, 0 game errors in the tests. Real run, first iterations
  (2,000 games, 8 workers, a third of the GPU): 107.7 and 105.4 s (play 45 s, PPO 57 s; meta-99 at full share 48.8 s), 0
  errors, 37 and 42 games cut; nvidia-smi 2–35% and 3.8–5.2 GB in use on the card (with about 1.5 GB of the desktop's).
- **Found:** (1) Forks are not common random numbers: from one state the first iteration's recorded transitions already
  differ between forks (3,189 / 2,995 / 3,592 in the smoke), so branch-to-main noise has to come from the A/A cards. (2) At a
  third of the GPU an h2h runs about 4.7 games/s with 4 workers (1,104 games in 235 s; #73's ladder: 78 games/s at full
  share and 14 workers), so a full 1,500-pair test (6,000 games) may take 10–20 minutes; an A/A card, with two answer-key
  evaluations of 4,608 games, about 30. (3) A grown slot-binding pilot does not start exactly as its source plays: slot
  binding also changes the count features of attached Energy.
- **Next:** The A/A cards at iteration 160: set elo1 from their spread before 003 and 004 are decided at 170; then meta
  cards with thresholds from the A/A's answer-key spread (draft reward of the result alone, `--draft-margin 0`; 6 swaps a
  draw; turnover 0.3); auxiliary value heads with game-general targets, still to build.

### #84 · 2026-10-18 · A4 · Auxiliary heads with game-general targets, queued as a lab card
- **Done:** The KataGo-style auxiliary heads recommended in `notes/analysis-2026-10-06.md` and never built, with targets any
  card game has. `TokenPointerNet(aux_heads=N)` (off by default; old checkpoints load and play unchanged): a small MLP on the
  pooled state, `aux_head`, outside forward's outputs, so play, ONNX and inference do not change. `rl/train.py`
  `aux_targets`: per decision, the deciding player's decisions left until its trajectory ends (log(1 + k) / log 201) and
  the trajectory's unshaped result, from the rollout batch alone (rows of a trajectory may be interleaved with others');
  `ppo_update` adds `--aux` × their squared error, through the shared trunk, and logs `aux_loss`. `rl/metagame.py --aux`
  computes the targets before the prize shaping; `token_net`, `rl/gpu_matrix.load_policy` and
  `notes/scripts/pilot_ablation.py` read the option; a grown pilot leaves `aux_head` at its initialisation. Card
  `005-pilot-aux` (`aux_heads 2`, `--aux 0.25`, two segments) queued behind 003 and 004.
- **Evidence:** `rl.tests` PASS, with new checks: `aux_targets` on hand-made interleaved trajectories; a pilot grown from
  another with `aux_heads 2` gives exactly its policy logits and value; the auxiliary loss has a gradient in the first
  encoder block; it exports to ONNX. One iteration of `rl.metagame` forked from meta-99 with `aux_heads 2` and `--aux 0.25`
  (40 games, 2 workers): 0 errors, `aux_loss` 0.719 on the first update, the head saved in the checkpoint.
- **Found:** `TokenPointerNet` already had an attribute `aux` (the embedding of each token's aux id); the first version of
  the head took that name and broke loading, caught by the tests before the running lab started a new process with it.
- **Next:** The card's result after 003 and 004; if it passes, the credit probe of #75 on the adopted pilot, to see whether
  the one-step value carries more of a move's effect.

### #85 · 2026-10-18 · A5 · The archived panel with SimpleBot on both sides: meta-99's best decks win 58% against the human lists
- **Done:** #69's open item, an evaluation that does not share the learned pilots' style: `rl/evaluate_agents.py`
  `sb_archived`, each of a population's best decks (by recent results) against the 24 archived lists with SimpleBot on both
  sides (`env/tools/evaluate.js --x simplebot --y simplebot --tokens`, the deck as D1 and the lists cycled as D2, both
  directions; `--sb-archived-games`, default 240 a deck). The lab's milestones run it (`rl/lab.py meta_metrics`
  `sb_archived_mean`); its branch evaluations skip it. Run on meta-99's snapshots at iterations 49 and 99 and its final
  checkpoint (`runs/meta-99/eval_sb_archived_it{0049,0099,0149}.json`).
- **Evidence:** 12 decks × 240 games per snapshot (2,880 games, about 2 minutes on 4 workers; SimpleBot against SimpleBot
  ran 24 games in 1 s on 3 workers in a check, with no errors or cut games). Mean against the 24 lists (standard error of
  one deck's rate about 0.03): iteration 49 0.467 (decks 0.35–0.66), 99 0.621 (0.57–0.67), 149 0.579 (0.55–0.62); the same
  decks with pilot-v2 on both sides (#69): 0.279 / 0.427 / 0.522.
- **Found:** (1) Under a pilot that is not one of the learned ones, the drafted decks do better against the human field, not
  worse: #69's worry that pilot-v2's habit of leaving draw Trainers unplayed flatters Trainer-light decks does not show
  here. SimpleBot is itself a weak heuristic player, so this measures the decks under simple play, not in a strong
  player's hands. (2) The two pilots order the snapshots differently: under SimpleBot iteration 99's decks are best (0.62
  against 0.58), under pilot-v2 iteration 149's (0.52 against 0.43); the population's median deck had 13 Trainers at
  iteration 100 and 5 at 149 (#69), so the Trainer-lighter meta is the one pilot-v2 rates higher. (3) SimpleBot is no longer
  the expensive evaluation the README's A0 numbers describe (0.6 games/s/core then, before the engine fixes of #3).
- **Next:** The lab's milestones now report this beside the pilot-v2 panel; the human field against itself under SimpleBot is
  0.5 by construction, so a drafted meta above 0.5 here and on the answer key's staples is the target.

### #86 · 2026-10-19 · A4 / A5 · The lab restarted; a restart bug fixed; the A/A cards set elo1 = 20 and a meta gain of 0.03
- **Done:** The lab was found stopped by a `runs/lab/STOP` file (23:53 on 10-18), with the main line at 160, card 001-aa-same
  run to 160 and 002-aa-reseed to 152, neither decided. Fixed a bug in `rl/lab.py lab_main` that this state exposes: a
  branch was decided only in the cycle that ran it to m, so a branch already at m after a restart (001) was never decided
  at m, and would have been run one more segment and decided at m + 10, against a main line two segments from its fork.
  Now a card is due at m if it started before m and has no rung at m; due cards behind m run first, then all due cards
  are decided. `run_meta_eval` reuses an existing output file, and the main line's answer key at m is one file
  (`tmp/meta_main_XXXX.json`) shared by every card decided at m. Restarted detached at 07:21 (RL_GPU_SHARE 0.333,
  RL_CPU_THREADS 10). Before either A/A card was measured, wrote the rule that turns them into thresholds into
  `notes/plan-lab.md` (σ = sqrt(max(0, mean Elo² − mean SE²)) on the drafted panel, elo1 = max(15, 2σ) rounded up to 5;
  a meta min_gain = max(0.03, 2 × RMS of the A/A answer-key differences) rounded up to 0.01), then applied it:
  `runs/lab/lab.json` elo1 20 and an `aa` record. Queued three meta cards, two segments each, rule archived_mean
  min_gain 0.03: `006-meta-margin0` (`--draft-margin 0`), `007-meta-swaps6` (`--swaps 6`), `008-meta-turnover30`
  (`--turnover 0.3`).
- **Evidence:** `rl.tests` PASS (30 s) with a new `check_lab_loop`: the lab loop with fake runs, a STOP during the second
  branch's segment, then a restart, decides 001 and 002 at 160 and a two-segment card at 170 and 180, each once; on the
  loop before the fix the same check fails (001 decided at 170). Milestone at 160 (main line, 23:32 on 10-18): answer key
  under pilot-v2 0.480 (best deck 0.659; 0.522 at 149, #69), staples 4.83 a deck, best overlap 0.533 (Wigglytuff),
  SimpleBot 0.902, SimpleBot on both sides against the archived lists 0.532 (0.579 at 149, #85). A/A at 160 (branch
  against main line):

  | card | drafted panel (6,000 games) | archived (1,104) | answer key, branch − main | staples | best overlap |
  |---|---|---|---|---|---|
  | 001-aa-same | +1.7 Elo [−5.3, 8.8] | −2.2 [−19.0, 14.6] | 0.7119 − 0.7191 = −0.007 | 3.42 − 4.83 | 0.45 − 0.53 |
  | 002-aa-reseed | −13.3 [−20.1, −6.4] | −17.0 [−35.0, 0.8] | 0.7188 − 0.7191 = −0.000 | 4.58 − 4.83 | 0.48 − 0.53 |

  σ = 8.8 Elo (SE 3.6 and 3.5), 2σ = 17.6, elo1 = 20; answer-key RMS 0.005, so the 0.03 floor binds; staples 2.04 and
  overlap 0.14 if a card uses them. A drafted-panel test of 6,000 games took 176 s and the archived one 39 s with 8
  workers (34 games/s; the smoke's 4.7 games/s was 4 workers at 40 games); a whole A/A decision took 5–7 minutes.
- **Found:** (1) A branch with no change can be a clearly different pilot after one segment (002: −13 Elo, its interval
  excluding 0): the training noise between forks is larger than the test's own, so a pilot change must be worth about
  20 Elo in one segment to pass, and smaller real gains will read as inconclusive. (2) The answer key under the main
  line's own pilot (0.72) is far above the same decks under pilot-v2 (0.48): the main line's pilot has never played the
  archived lists, so this measure also rewards its familiarity with its own decks; it is shared by both sides of a meta
  card, so the comparison stands, but its level is not comparable with #69. (3) Staples and overlap move by 1.4 and 0.08
  between A/A branches, so the answer-key mean is the only steady meta metric. (4) Every deck takes one sampled draw (3
  cards) an iteration, so the population is close to the draft head's own distribution, and its median composition
  swings over tens of iterations (Pokémon/Trainer/Energy 39/7/13 at iteration 20, 19/22/17 at 40, 14/13/33 at 100,
  22/4/33 at 145, 22/12/26 at 159); the 12 best decks at 160 average 22/13/25.
- **Next:** 004 (2 epochs, noninferior) decided at 170 and 003 (value cross-attention) at 180 against elo1 20; then 005
  (auxiliary heads), and the meta cards in name order.

### #87 · 2026-10-19 · A4 · First adoption: 2 PPO epochs; cards running at an adoption are rebased
- **Done:** The lab decided its first pilot card at iteration 170 and adopted `004-pilot-epochs2` (`--epochs 2`, a
  noninferiority test: H0 Elo <= −20 against H1 Elo >= 0): the main line goes on from the branch's checkpoint with
  `--epochs 2` in `main_args` (`runs/lab/main/lineage.jsonl`; the old state kept as `seg_0170.before-004-pilot-epochs2.pt`).
  This exposed a gap: `003-pilot-vq4` (two segments, forked at 160) would have been decided at 180 against a main line that
  contains 004, and its second segment would have run with `--epochs 2` too, because a branch's arguments are the main
  line's merged with the card's. `rl/lab.py`: after an adoption, every card still running from an earlier fork is closed
  as "rebased" and queued again as `<id>-b` (`requeue`), which starts from the new main line; the retest copy of a card
  that passed but was not adopted now keeps the card's `"test"` (it dropped it, so a noninferiority card would have been
  retested for superiority). Stopped the lab by its STOP file (main line at 172), rebased 003 by hand the same way
  (`003-pilot-vq4-b` queued, an event recorded), and restarted it at 08:45 with the new code.
- **Evidence:** 004 at 170: drafted panel +8.7 Elo [−9.7, 27.1], H1 after 200 pairs (800 games, 24 s); archived lists
  +40.5 [22.4, 58.8] (1,104 games, H1 of the gate's test). Its segment took 14.7 minutes against the main line's 18.1, and
  the main line's first iteration with 2 epochs 92.1 s against 108.3 s. 003's early check at 170 (only "clearly worse"
  stops it): −14.3 Elo [−26.1, −2.5] over 2,000 games, verdict none. `rl.tests` PASS; `check_lab_loop` has a second
  scenario: a one-segment card passes at 160 while a two-segment card runs, and the loop adopts it, closes the other as
  rebased and decides its `-b` copy at 170 and 180 from base 160.
- **Found:** (1) On the archived lists the 2-epoch branch beat the main line by 40 Elo after one segment, outside both A/A
  cards' archived results (−2 and −17): fewer passes over each batch may fit the drafted decks less narrowly. One fork,
  so not established; the next milestones under pilot-v2 and SimpleBot will show whether the main line's play on the human
  lists moves. (2) 003's early result (−14) is the size of the reseeded A/A branch's (−13), so it says nothing yet.
- **Next:** 005 (auxiliary heads) checked at 180 and decided at 190; `003-pilot-vq4-b` from 180, decided at 200; then the
  meta cards. Milestone at 200.

### #88 · 2026-10-19 · A4 · Auxiliary heads fail in the lab; value cross-attention passes its early check
- **Done:** The lab decided `005-pilot-aux` (auxiliary heads on the pooled state, `aux_heads 2`, `--aux 0.25`: decisions
  left until the game ends and the final result, #84; two segments from 170 on the 2-epoch main line) at 190: failed,
  closed. `003-pilot-vq4-b` (value cross-attention, restarted from 180, #87) passed its early check at 190 and runs to
  200. `006-meta-margin0` started at 190. No code changes.
- **Evidence:** 005 at 180 (early, "clearly worse" only): +15.6 Elo [−8.1, 39.6], 400 games; at 190 (H0 Elo <= 0 against
  H1 Elo >= 20): −22.6 [−48.9, 3.4], H0 after 100 pairs (400 games). Its auxiliary loss 0.393 at iteration 170, 0.271 at
  176, 0.27–0.29 from then to 189; value loss 0.096–0.101 in the branch and 0.097–0.106 in the main line over the same
  iterations; games cut at the decision cap 14–69 an iteration in the branch (62–69 at 185–189) and 7–45 in the main line.
  003-b at 190: +1.7 [−12.6, 16.1], 1,200 games, not clearly worse.
- **Found:** (1) The auxiliary targets are learned in a few iterations and then add nothing the value loss shows, so at
  weight 0.25 they did not give the trunk a signal the lambda-return lacked, at least within two segments. (2) A card's
  reading swings by about 40 Elo between its two segments (+16, then −23), the training noise of #86 plus a 400-game
  interval of ±26: the sequential test stops at its first look of 100 pairs when the estimate is far from elo1, which is
  correct for "is it 20 Elo better", but it means a rejected card is only shown not to be a large gain. (3) The branch's
  cut games rose late in its second segment, unexplained; not followed up since the card is closed.
- **Next:** 003-b decided at 200 with the milestone at 200; 006 decided at 210.

### #89 · 2026-10-19 · A4 / A5 · Value cross-attention fails; milestone 200: every best deck above half against the human lists under pilot-v2; three pilot cards queued
- **Done:** The lab decided `003-pilot-vq4-b` (value cross-attention, 4 queries, trained with the trunk; two segments from
  180 on the 2-epoch main line) at 200: failed, closed. Milestone at 200 (`runs/lab/main/eval_it0200.json`). `006-meta-margin0`
  finished its first segment (190 → 200, no test until 210) and `007-meta-swaps6` started at 200. Queued three pilot cards,
  two segments each, behind 008: `009-pilot-ent02` (`--ent 0.02`; #81–82 tried only 0.001), `010-pilot-slotbind`
  (`slot_bind`, #71/#74) and `011-pilot-lr2` (`--lr 2e-4`, never screened). Smoke of 010's fork: one iteration of 40 games
  on 2 workers from `seg_0190.pt` with `--pilot-opts {"slot_bind": true}` (run dir deleted after).
- **Evidence:** 003-b at 190 (early): +1.7 Elo [−12.6, 16.1]; at 200: −0.9 [−14.3, 12.5], H0 (Elo <= 0 against >= 20) after
  400 pairs (1,600 games). Milestone, iteration 160 → 200 (the 12 best decks by recent results): against the 24 archived
  lists under pilot-v2 0.480 → 0.681 (decks 0.22–0.66 → 0.51–0.73), with SimpleBot on both sides 0.532 → 0.588 (0.41–0.64
  → 0.52–0.64); the main line's pilot against SimpleBot 0.902 → 0.954; staples 4.83 → 4.17 a deck; best overlap 0.533 →
  0.517, nearest list Wigglytuff for 11 of 12 and Electabuzz / Mr. Mime for one, at both; the best decks average
  Pokémon/Trainer/Energy 22.1/13.4/24.5 → 20.2/10.9/28.9. Smoke: 0 errors, the checkpoint's config has `slot_bind` True,
  first value loss 0.174 (the main line's 0.096–0.106).
- **Found:** (1) Value cross-attention is now closed both ways: worse on a frozen trunk (#78) and no better trained with it
  (−1 Elo after two segments). (2) The main line's best decks rose by 0.20 against the human lists under pilot-v2 in 40
  iterations that include the 2-epoch adoption at 170, but only by 0.06 under SimpleBot, and they moved toward more Energy
  and fewer Trainers, the shape #85 found pilot-v2 rates higher; so most of the pilot-v2 rise may be that panel's style,
  and SimpleBot's 0.59 (0.62 at meta-99's iteration 99) is the steadier reading. Neither can be credited to the adoption,
  since the main line has no control. (3) Three pilot cards decided so far: one adopted (2 epochs, a noninferiority test) and
  two failed against elo1 20 (auxiliary heads, value cross-attention), with value cross-attention's first fork rebased.
- **Next:** 006 decided at 210, 007 at 220; then 008 and the pilot cards 009–011. Milestone at 240 for the stall rule.

### #90 · 2026-10-19 · A5 · The result-only draft reward fails its answer-key rule but trains a stronger pilot; replication queued
- **Done:** The lab decided `006-meta-margin0` (`--draft-margin 0`: the draft head's reward is the result alone, without
  the end-of-game prize margin at weight 0.5; two segments from 190) at 210 by its rule (archived_mean gain >= 0.03, pilot
  not clearly worse): failed, closed. `007-meta-swaps6` passed the midpoint of its two segments; `008-meta-turnover30`
  started at 210. Queued `006-meta-margin0-n`, written after 006's result and saying so: a fresh fork of the same change
  from the main line at 220 as a pilot card with a noninferiority test (H0 Elo <= −20 against H1 Elo >= 0, the archived
  gate), two segments, on the grounds that the result-only reward is the simpler and more general method (the precedent
  is 004's speed-up), so the answer key is not consulted for it again.
- **Evidence:** Answer key at 210, both populations' 12 best decks against the 24 archived lists under the main line's
  pilot: main 0.794 (decks 0.73–0.84), branch 0.812 (0.77–0.86), gain +0.018; staples 3.42 / 3.25, best overlap 0.45 /
  0.48, no deck at half overlap with any list; best decks' Pokémon/Trainer/Energy 21.5/8.6/29.9 and 20.6/9.4/30.0. Pilot
  gate (500 drafted pairs, 2,000 games, fixed length): branch +29.6 Elo [18.6, 40.7] against the main line's pilot.
- **Found:** (1) The draft margin enters only the draft head's reward (`rl/metagame.py` line 218), so the branch's pilot
  differs from the main line's only by the decks it trained on for 20 iterations, yet it is 30 Elo stronger, with an
  interval excluding both 0 and the A/A spread (σ ≈ 9 Elo a segment from two cards, #86). Whether this is the change or a
  lucky fork is what the replication tests. (2) Under the main line's own pilot the answer key keeps rising (0.719 at 160,
  #86; 0.794 at 210), partly the familiarity effect of #86, while staples a deck fell from 4.83 to 3.42 and no best deck
  is at half overlap with any archived list: the decks beat the human lists more, but resemble them less.
- **Next:** 007 decided at 220, then `006-meta-margin0-n` from 220 (decided at 240, with the milestone), 008 at 230.

### #91 · 2026-10-19 · A5 · Second adoption: 6 swaps a draw; the rebase rule fires
- **Done:** The lab decided `007-meta-swaps6` (`--swaps 6`, two segments from 200) at 220 by its rule (archived_mean gain
  >= 0.03, pilot not clearly worse): passed and adopted; `main_args` now has `--swaps 6` and `--epochs 2`. The rebase rule
  of #87 fired for the first time: `008-meta-turnover30` (forked at 210) was closed as rebased and `008-meta-turnover30-b`
  started from the new main line at 220, with `006-meta-margin0-n` (#90).
- **Evidence:** Answer key at 220 under the main line's pilot: main 0.695 (best deck 0.822, staples 2.25 a deck), branch
  0.823 (0.861, 3.83), gain +0.128; best overlap 0.483 for both. Pilot gate: +2.8 Elo [−8.3, 13.9], 2,000 games.
- **Found:** Most of the gain is the main line's own fall: its answer key dropped from 0.794 at 210 (#90) to 0.695 at 220
  while its median deck went from 8 Trainers to 2–3 (16–17 of 99 decks with none, #92), and the branch, forked at 200,
  kept a median of 13 at 210. So the card shows that the 6-swap line did not collapse in these 20 iterations, not that
  6 swaps prevent it; adopting it also put the main line back on Trainer-carrying decks.
- **Next:** 006-n and 008-b decided at 240 with the milestone.

### #92 · 2026-10-19 · A4 / A5 · Why the decks drop Trainers: the pilot cannot set up before attacking, and the drafting follows it
- **Done:** At Evan's question ("why there are no trainers, and if not, what is wrong with the pilot that it can't use
  trainers"; then "Trainers are certainly good and we can treat the human lists as ground truth ... if it is using way
  more energy then it isn't correctly drafting or playing"), four diagnostics, evaluation only:
  (1) the main line's Trainers over time and the draft head's choices (`log.jsonl` `best[].top_in / top_out`, `draft.h_in`);
  (2) `notes/scripts/trainer_value.py` (new): each deck against a copy of itself with one group of Trainers (by card name:
  draw = Oak, Bill, Gambler; search = Computer Search, Item Finder, Energy Retrieval, Nightly Garbage Run, ...; disrupt =
  Energy Removal, Super Energy Removal, Rocket's Sneak Attack, Lass, ...; tempo = Gust of Wind, PlusPower, Scoop Up,
  Switch, ...) replaced by its most common basic Energy, one player on both sides, 64 games a pair, the same deals per
  deck for the learned pilots (`notes/data/eval/trainer_value_{archived,archived_trained,drafted200}.json`);
  (3) the A2 lethal puzzles, never generated before: `env/tools/puzzles.js generate` (two processes, 400 heuristic games
  on the archived lists) gave 408 "win this turn" positions with provable answers (`notes/data/puzzles/lethal.json`);
  `score` now takes `onnxtok:` token models and `--json`; (4) `env/tools/trainer_trace.js` (new): one pilot on both
  sides over the archived lists, and for every Trainer played in a main phase whether the turn goes on to attack and
  take a prize, against the player's turns overall (120 games each, `runs/puzzles/trace_*.json`). Also the Trainer probe
  of #79 on the main line at 220 for play rates only (`--max-options 2 --rollouts 2`); `notes/scripts/credit_diag.py`
  `focus_table` now keeps p_play for a card offered but not among the probed options (it crashed on them). Pilots: the
  main line at 220, pilot-v2, and as one-off diagnostics two pilots trained on the archived lists, `a4-tok` it249 (#26,
  93% against SimpleBot) and `arch-A` (#49); pilot-v2 and a4-tok were exported at 256 tokens and 128 options (their
  configs say 128 / 48; neither size enters a weight).
- **Evidence:** (1) Population median Trainers 5 at 150, 15 at 162–165, 6 at 186, 12 at 201–204, 2 at 216; at 219 16 of
  99 decks have none, Bill is in 3% of decks (87% at 200), the 24 archived lists median 28 (26–30). The draft head's
  incoming choice has entropy 0.2–1.1 nats against about 6 for a uniform pick, and its top-3 incoming mass on the best
  decks moves by kind: basic Energy 0.84 at 100, Trainers 0.6–0.8 at 155–180, special Energy 0.6–0.9 at 185–200, basic
  Energy 0.91–0.93 at 210–215. (2) Score of the archived list against its copy with the group replaced (± 95%):

  | player | all | draw | search | disrupt | tempo |
  |---|---|---|---|---|---|
  | main line at 220 | 0.672 [0.63, 0.71] | 0.666 | 0.424 | 0.461 | 0.413 |
  | pilot-v2 | 0.653 | 0.643 | 0.424 | 0.457 | 0.365 |
  | a4-tok (trained on these lists) | 0.789 | 0.712 | 0.480 | 0.503 | 0.409 |
  | arch-A (fine-tuned on 6 of them) | 0.748 | 0.762 | 0.477 | 0.521 | 0.465 |
  | SimpleBot | 0.433 | 0.490 | 0.379 | 0.397 | 0.333 |

  Intervals ±0.02–0.05; 27.5 / 5.9 / 7.3 / 6.5 / 8.0 cards replaced on average. On the main line's 12 best decks at 200
  under its pilot: all 0.565, draw 0.533, search 0.473, disrupt 0.517. (3) Puzzles: 262 won by an attack, 97 only by a
  Trainer first, 49 by another move first. Solved (greedy): attack-won 90% (main line), 94% (pilot-v2), 86% (a4-tok),
  92% (heuristic), 47% (random); Trainer-first 60 / 58 / 61 / 62 / 47%; the 16 won only through PlusPower 31% for all
  three pilots, 94% heuristic, 25% random, the pilots' commonest choice there attacking at once (6–8 of 16). The share
  of winning first moves is 0.51 (Trainer-first) and 0.45 (attack-won), so random's 47% is the floor of both.
  (4) Same-turn attack / prize after a Trainer, against all turns:

  | pilot | all turns | PlusPower | Gust of Wind | Super Energy Removal | Energy Removal |
  |---|---|---|---|---|---|
  | main line, sampled | 54.1% / 10.7% | 37.5 / 9.0 | 28.3 / 4.0 | 23.5 / 1.5 | 44.4 / 9.4 |
  | main line, greedy | 61.7 / 12.1 | 42.6 / 9.2 | 28.2 / 0.7 | 34.6 / 5.9 | 47.3 / 9.0 |
  | pilot-v2, sampled | 48.1 / 11.9 | 40.2 / 8.5 | 26.2 / 1.9 | — | 40.6 / 7.8 |
  | a4-tok, sampled | 50.1 / 10.1 | 39.0 / 11.4 | 32.7 / 7.7 | 26.0 / 4.3 | 44.1 / 4.5 |

  0 errors in every trace. Probe at 220 on the archived lists, the pilot's probability of playing a Trainer where one is
  offered: any 0.284 (base it79 0.225, base-cont 0.326, #82), Energy Removal 0.617, Bill 0.565, Oak 0.458, Item Finder
  0.411, Computer Search 0.390, Gust 0.341, PlusPower 0.336. Engine and inputs checked: PlusPower (+10 after Weakness and
  Resistance, discarded at the end of the turn), Gust of Wind and Computer Search match their text; the per-turn cap is
  250 decisions; the pilot's inputs carry each Pokémon's HP and damage (`env/tokens.js` slot features), each attack's
  damage (`rl/token_model.py` card features) and attached Trainers such as PlusPower (TOOL tokens).
- **Found:** (1) With the human lists as ground truth, every pilot built so far misplays most Trainers: only the draw
  group (Oak, Bill) is worth more than basic Energy to it (+14 to +26 points), while search, disruption and tempo cards
  are worth less (0.36–0.52), for pilots trained on those very lists too. Practice helps (a4-tok, all Trainers 0.79
  against the main line's 0.67) but does not fix it. (2) What is missing is setting up before attacking: the pilots solve
  attack-won lethals like the heuristic but Trainer-first ones barely above random, PlusPower-then-attack at random, and
  they play PlusPower and Gust on turns that attack less often than their average turn (Gust then a prize: 0.7% greedy).
  The information is in their inputs and the cards work, so it is the learning: a one-action-at-a-time policy whose
  value carries a small share of a move's effect (#75) learns "attack now" and not the conditional "this setup makes the
  attack a Knock Out". #68's "attacks before drawing" is the same failure. (3) The drafting follows: the draft head
  learns from results under this pilot, for which most Trainers are worse than an Energy, and its incoming choice has
  collapsed onto one card kind at a time, which it moves between, so the population swings (2–15 Trainers) and is at
  its low now. SimpleBot is no yardstick for Trainers either: it plays an Item only if its one-step heuristic score
  rises, so PlusPower and Gust, which pay after the attack, are invisible to it (0.33–0.40). (4) psearch (#50, the
  pilot's top moves played to the end of the turn in re-dealt copies, scored by its value) gained nothing against
  SimpleBot but was never measured on Trainer use or on these puzzles.
- **Next:** Evan's call on giving the pilot in-turn lookahead: first measure psearch over the main line's pilot on the
  puzzles and the Trainer-value panel (whether lookahead within the turn fixes Trainer-first play), then, if it does,
  expert iteration on it with the puzzles and the Trainer-value panel as the yardstick instead of SimpleBot; separately,
  the draft head's collapsed incoming choice.

### #93 · 2026-10-19 · A5 · Practice before a draw counts: seasons in the metagame loop, queued as a lab card
- **Done:** At Evan's direction ("It should probably practice each deck it drafts before playing it in a setting that
  counts towards reward"): `rl/metagame.py --season K --candidates C`. Until now every game gave each side a fresh draw,
  so a draw was judged by the one game in which the pilot first held that deck. With K > 1, at the start of a season
  (iteration % K == 0) every deck draws C candidates from the head; every game of the season plays one of the side's
  candidates at random; PPO runs every iteration as before (the practice); only the season's last iteration feeds the
  REINFORCE step, whose leave-one-out baseline over the deck's games then compares its candidates after the same
  practice; at the season's end every deck moves to one of its candidates at random (still a sampled draw, now a
  practised one). A deck that turnover brings in mid-season draws its candidates at once. The held candidates are saved
  in the checkpoint (`season`), so a resume continues the season. `--season 1` (the default) is the old loop unchanged:
  no extra random draws and the same updates. Lab card `008a-meta-practice` (`--season 5 --candidates 4`, three
  segments, archived_mean min_gain 0.03), named to start next, at 240.
- **Evidence:** `rl.tests` PASS. Smoke (`runs/_smoke-season`, deleted after; forked from `seg_0220.pt`, season 2, 2
  candidates, 40 games an iteration, 2 workers), stopped after iteration 220 and resumed to 224: `counted` false / true /
  false / true at 220–223, the draft head updated only at 221 and 223; the population after 220 equal to the fork's; 99
  decks × 2 candidates held across the resume; a second resume of the 221 checkpoint through its counted iteration left
  99 of 99 decks equal to one of their held candidates; 0 errors.
- **Found:** Practice addresses the drafting's judgement, not the pilot's skill: a4-tok, trained 250 iterations on the
  human lists, gets more from their Trainers than the main line's pilot (0.79 against 0.67, #92) but still solves the
  PlusPower lethals at random's rate. At this card's scale a candidate gets about 10 games an iteration, so 40 games of
  practice in a season, inside a pilot shared with 98 other decks; whether that is enough practice to move the drafting
  is what the card measures.
- **Next:** 008a from 240, decided at 270, with the population's Trainer counts beside the answer key; the in-turn
  lookahead question of #92 remains open.

### #94 · 2026-10-19 · Plan · Evan's ideas first; his untried architecture ideas as held lab cards; the rediscovery plan
- **Done:** At Evan's direction ("Opt for trying fully out the ideas that I give and logging them, rather than continuing
  with what was going before. I'd like a log of all of the messages I sent that you tried and didn't try"):
  `notes/evan-requests.md`, every message of his as recorded (this session verbatim, earlier ones as the log and
  notes quote them) with tried / partly / not tried and where. Two of his earlier ideas had never been fully tried:
  memory for the pilot (10-14; built in #76, never run) and the deck-free board encoder on the main line (10-13;
  screened once from scratch, #73). Both are now lab cards: `009-pilot-hist4`, `009-pilot-memattn`,
  `009-pilot-memgru` (two segments each) and `009-pilot-deckcross` (three segments, noninferiority). The practice idea
  (#93) also got a stronger variant, `008b-meta-practice10` (season 10, 2 candidates, four segments). My cards were
  renamed to run after his (`030-pilot-ent02`, `031-pilot-slotbind`, `032-pilot-lr2`). To run all of them together:
  - lab `branches` 4 (`lab.json`);
  - `rl/lab.py`: a card with `"hold": true` that passes is marked `passed-held` and not adopted, so the cards running
    beside it keep their control; the four architecture cards are held while the practice cards run;
  - `rl/train.py` `NEW_WEIGHTS` lets a branch grow the memory core (`mem_*`, which starts at zero through `mem_out`),
    history embeddings (`hist_*`) and the separate deck encoder (`deck_null`, `deck_blocks`, `fuse`); at growth the
    fusion's output layers start at 0 (`ZERO_AT_GROWTH`), so a grown deck-free pilot starts deck-blind rather than at
    random;
  - `rl/metagame.py` passes the pilot's history window to its game workers (it never did, so a history pilot in the
    loop would have seen no history).
  The lab was stopped by its STOP file at 240 and restarted with this code at 13:56. Then, at Evan's request ("synthesize
  my comments and all of the previous tests into a new iterative plan ... that will rediscover the ground truth of the
  human decks"): `notes/plan-rediscovery.md`, for his review. It has the gap today (best decks 20 / 11 / 29
  Pokémon / Trainers / Energy against the human lists' 13.5 / 28 / 18), what the tests add up to, a scorecard with
  targets (pilot competence on the human lists' cards, strength, deck shape, the answer key under a pilot that plays
  Trainers correctly, drafting health), a loop that works on the largest gap upstream first (the pilot before the
  drafting), stages A–D with their candidate changes, and five questions for Evan.
- **Evidence:** `rl.tests` PASS, with a third `check_lab_loop` scenario: a held card that passes is not adopted, and
  the two-segment card beside it is decided at 170 and 180 without a rebase. One-iteration forks of the main line at 230
  (40 games, 2 workers) with `history 4`, `memory gru`, `memory attn` and `deck_mode cross`: 0 errors each, PPO run (value
  loss 0.103 / 0.122 / 0.087 / 0.292; the deck-free one starts deck-blind); each played a 10-pair `rl.lab h2h` against
  the main line without error.
- **Next:** Evan's review of the plan. Meanwhile the lab runs his cards: practice (`008a`, `008b`) and the
  architecture cards, after the decisions at 240.

### #95 · 2026-10-19 · Plan · The rediscovery plan cut to three stages of three steps
- **Done:** At Evan's request ("Simplify to three stages with three steps each"): `notes/plan-rediscovery.md`
  rewritten. Stage 1, the pilot plays the human field's cards correctly: (1) Evan's memory and deck-free-encoder cards
  (running), (2) lookahead within the turn (measure play-time search, then expert iteration with lines scored by the
  game's own outcome within the turn), (3) credit and exploration within the turn (λ = 1 inside a turn, prize shaping
  kept on, entropy 0.02). Stage 2, the drafting finds the human deck shape: (1) practice before a draw counts (running),
  (2) drafting with the Stage 1 pilot, (3) an entropy floor on the incoming choice and the result-only reward.
  Stage 3: the headline run from scratch, Worlds 2005 unchanged, then Magic. The scorecard is now six rows. The pilot's
  strength against SimpleBot on the human lists is marked as not yet measured: the earlier draft showed the pilot's rate
  on its own decks there.
- **Evidence:** Text only.
- **Next:** Evan's review (four questions at the end of the plan).

### #96 · 2026-10-19 · A4 · Stage 1 started: in-turn search fixes setup at play time; expert iteration, turn-level credit and a competence score in the lab
- **Done:** Evan approved the plan ("Sure try it"), read as approval of its four questions as proposed (prize shaping
  kept on; the game's own score inside the turn search; pilot changes decided on the puzzles and the Trainer-value panel
  with 2005 held out; the targets). Stage 1, step 2, measured first: `env/tools/puzzles.js score` takes
  `psearch:<onnx>:k:dets` (#50's PolicySearchAgent over the pilot). Then:
  - **Turn-level credit:** `rl/train.py advantages(..., lam_turn)` uses lam_turn between decisions of the same game
    turn (glob byte 0, which is the turn exactly up to 240) and lam across turns; `rl/metagame.py --lam-turn`.
  - **Expert iteration:** `env/runner.js` jobs with `untilTurnEnd` stop at their first asked decision after the turn
    they started in and report `stopped { player, value }`. `env/remote_worker.js tsearch` is `games` (the same jobs,
    recordings and results; `games` takes an `onDecision` hook) plus probes at a share of the recorded main-phase
    decisions; each probe's options (all up to `maxOptions`, else the one played and a random sample) are played `lines`
    times from copies re-dealt for the deciding player, greedily to the end of the turn, scored by the result, or by the
    pilot's value after the turn plus `prizeWeight` a prize taken. `rl/metagame.py --distill b --search-p --search-max
    --search-options --search-lines --search-prize --search-margin` sends `tsearch`, sets each probe's best option as
    the target of its recorded decision (only where the options' scores differ by more than the margin), and logs
    `search`; `ppo_update` adds b times the cross-entropy toward the target, averaged over a minibatch's searched
    decisions (`distill`, `distill_agree` in the stats).
  - **The competence score:** `rl/lab.py run_s1` is the Trainer-value panel on the archived lists (search, disrupt and
    tempo groups, 64 games a pair) and the greedy pilot on the 408 puzzles; `s1` is the mean of search, disrupt, tempo,
    Trainer-first and PlusPower-only. Milestones now report it, and pilot cards with `"decide": "s1"` are decided by its
    gain (`s1_min_gain`) with the drafted-panel Elo test as a gate (not clearly worse). Its A/A spread from the A/A cards'
    checkpoints at 160 sets `s1_min_gain` 0.06 (`lab.json aa_s1`). The lab was restarted with this code at 14:42.
  - **Cards** (all `"decide": "s1"`, two segments): the memory cards `009-pilot-hist4 / memattn / memgru` (set before
    they started); `009x-pilot-exit` (`--distill 0.3`, 10% of recorded decisions, 2 a game, 6 options, 2 lines) and
    `009x-pilot-exit-strong` (`--distill 1.0`, 25%, 4, 8 options, 4 lines, `--search-prize 0.1`); `010-pilot-lamturn`
    (`--lam-turn 1`), `010-pilot-shapeon` (`--shaping 0.1` that never fades) and `010-pilot-ent02` (renamed from 030).
- **Evidence:** Puzzles, the main line's pilot at 220, greedy against play-time search (k options, 4 re-dealt copies
  each, played to the end of the turn):

  | | attack-won (262) | Trainer-first (97) | PlusPower only (16) | all (408) |
  |---|---|---|---|---|
  | greedy | 90.5% | 59.8% | 31.3% | 79.2% |
  | psearch k 4 | 92.7% | 84.5% | 81.3% | 89.0% |
  | psearch k 8 | 92.7% | 87.6% | 81.3% | 90.2% |

  The competence score's A/A at 160: main 0.434 (search 0.401, disrupt 0.474, tempo 0.373, Trainer-first 0.608,
  PlusPower 0.313), 001-aa-same 0.398, 002-aa-reseed 0.439; differences −0.035 and +0.006, RMS 0.025, so the bar is
  max(0.03, 2 RMS) = 0.06. Most of the spread is the 16 PlusPower puzzles (0.31 against 0.19, two puzzles).
  `rl.tests` PASS with `check_lam_turn` (hand-made interleaved trajectories: lambda 1 inside a turn and lam across
  turns; `None` the ordinary GAE) and a distillation check in `check_train` (the reported cross-entropy equals the
  directly computed one before the step, the step lowers it, and at weight 0 the targets change nothing). One-iteration
  forks from `seg_0240.pt`, 40 games on 2 workers: `--lam-turn 1` 0 errors; `--distill 1 --search-p 0.3`: 36 searched
  decisions, 31 targets, 20 of them a different option from the one played, 344 lines in 1.0 s, 0 line errors, the
  cross-entropy 2.68 and agreement with the search 35% before the step, pre-clip gradient norm 27 (so weight 1 makes
  distillation the larger part of the step).
- **Found:** (1) The pilot already ranks the winning setup move among its top 4 in most Trainer-first lethals; what it
  lacks is seeing that the move wins, which looking to the end of the turn supplies (Trainer-first 60 → 85–88%,
  PlusPower 31 → 81%). So the in-turn sequencing failure of #92 is fixable by lookahead, and the question is whether
  training toward the search's choices puts it into the policy. (2) The competence score is coarse in its PlusPower part
  (16 puzzles); its bar is set accordingly.
- **Next:** The lab's cards in order: Evan's practice and architecture cards, then expert iteration, then turn-level
  credit, prize shaping and entropy, each decided on the competence score; 006-n (result-only draft reward) passed at 240.

### #97 · 2026-10-19 · A5 · At 240: the result-only draft reward adopted, turnover 0.3 failed, Evan's cards started
- **Done:** The lab decided its two cards at 240. `006-meta-margin0-n` (the draft reward from the result alone, a
  noninferiority pilot test, #90) passed and was adopted: `main_args` now has `--draft-margin 0` beside `--swaps 6` and
  `--epochs 2`. `008-meta-turnover30-b` (turnover 0.3) failed its answer-key rule. Four cards started at 240 in the four
  slots: `008a-meta-practice`, `008b-meta-practice10`, `009-pilot-deckcross` and `009-pilot-hist4`.
- **Evidence:** 006-n: pilot +0.0 Elo [−11.3, 11.3] after 1,600 games (H1 of "not clearly worse"), archived gate −13.2
  [−30.3, 3.8], not clearly worse. 008-b: answer key 0.792 against the main line's 0.780 (+0.012, rule 0.03), pilot −1.6
  [−11.9, 8.7].
- **Found:** The result-only reward's first fork came out 30 Elo stronger (#90) and its replication even, so the gain
  was that fork's luck; it is adopted for being simpler and more general, as the card said.
- **Next:** 008a / 008b at 270 / 280; deck-cross at 270, hist4 at 260.

### #98 · 2026-10-19 · A4 · The deck-free encoder stopped by its deck-blind start; a warm start for changed architectures
- **Done:** At 250 the lab stopped `009-pilot-deckcross` after its first segment (clearly worse), passed the early check
  of `009-pilot-hist4`, and started `009-pilot-memattn` in the freed slot. The deck-free pilot had started deck-blind
  by construction (#94), so the stop measured that handicap, not Evan's idea. To give the idea (and any change that
  cannot be grown as the identity) a fair start: `rl/warmstart.py`. The main line's pilot (the teacher) plays its own
  population's decks, sampled as in training, both seats recorded (with the student's history window if it reads one).
  A student of the new architecture, grown from the teacher's weights, is trained to match the teacher's policy (KL
  over the legal options) and value (squared difference, weight 1) for some epochs. Games are held out to measure the
  fit, and the result is written as a metagame checkpoint (the teacher's whole state with the student's net, config and
  optimizer). `rl/lab.py`: a card with `"warm": {"pilot-opts", "games", "epochs"}` runs it at the fork from the main
  line's state at the card's base (`run_warm`, an event `warm`) and forks the branch from it. Queued
  `009-pilot-deckcross-w` (2,000 games, 3 epochs; three segments, noninferiority, held). Also measured the scorecard's
  strength row, and restarted the lab with the new code at 16:18.
- **Evidence:** deck-cross at 250: −54.3 Elo [−77.5, −31.5], 400 games, H0 of "clearly worse". hist4 at 250: +22.6
  [−3.3, 48.8], 400 games. Warm start of the deck-free pilot from `seg_0250.pt`, held-out states: 40 games and 1
  epoch, KL 0.820 → 0.340, agreement 0.567 → 0.657, value MSE 0.290 → 0.878 (a small sample); 400 games (59,735
  states) and 2 epochs with value weight 1, KL 0.857 → 0.155, agreement 0.550 → 0.770, value MSE 0.864 → 0.070, in
  107 s. `rl.tests` PASS, with a fourth `check_lab_loop` scenario: a warm card's first segment forks from its warm
  checkpoint and a plain card's from the main line's state. Strength row: the main line's pilot at 240 against
  SimpleBot on the 24 archived lists (`evaluate.js`, greedy, 480 games both ways) 82.1% ± 3.4, the same as pilot-v2
  (82%); target 90%.
- **Found:** (1) The lab's early stop judges every two-segment card after one segment, which is fair to a change that
  starts as the identity and unfair to one that cannot. Warm starts remove the handicap at a few minutes a card.
  (2) History tokens, which also do not start as the identity, came out ahead after one segment anyway.
- **Next:** hist4 decided at 260 on the competence score; the warm deck-free card at the next free slot.

### #99 · 2026-10-19 · A4 / A5 · At 260: history tokens and the attention memory fail; the practice cards hold the Energy shape so far
- **Done:** The lab decided `009-pilot-hist4` (history tokens of the last 4 turns, Evan's memory question of 10-14) on the
  competence score at 260: failed. `009-pilot-memattn` (the attention memory, which starts as the identity) was stopped
  after its first segment as clearly worse. `009-pilot-deckcross-w` (warm start) and `009-pilot-memgru` started at 260.
- **Evidence:** hist4 competence 0.421 against the main line's 0.437 at 260 (gain −0.016, bar 0.06): search 0.427 /
  0.425, disrupt 0.451 / 0.442, tempo 0.367 / 0.375, Trainer-first puzzles 0.608 / 0.567, PlusPower 0.250 / 0.375;
  the Elo gate +0.2 [−12.1, 12.4] after 2,000 games (its +22.6 at 250 was noise). memattn at 260: −18.3 [−31.0, −5.6]
  after 1,600 games, H0 of "clearly worse". Median Trainers / Energy at the practice cards' counted iterations: 008a
  (season 5) 8/35 at 249, 8/36 at 254, 8/34 at 259; 008b (season 10) 7/36 at 249, 8/35 at 259; the main line 8/35 at
  243, 10/33 at 248, 11/31 at 253, 12/31 at 258.
- **Found:** (1) The main line's competence is flat: 0.434 at 160 (the A/A measurement) and 0.437 at 260, so 100 more
  iterations of ordinary training did not teach it to set up, which is what Stage 1's expert iteration targets.
  (2) History tokens and an attention memory over the player's own decisions do not supply what is missing; the GRU
  memory is the last of Evan's memory forms. (3) In their first two seasons the practice cards keep the Energy shape
  (8 Trainers, 34–36 Energy) while the main line's swings to 12 / 31; their answer-key decisions come at 270 and 280.
- **Next:** 008a at 270, deck-cross-w and memgru at 270–280, 008b at 280; then expert iteration.

### #100 · 2026-10-19 · A4 / A5 · At 270: practice before counting (season 5) fails; the warm-started deck-free encoder leads
- **Done:** The lab decided `008a-meta-practice` (Evan's practice idea, seasons of 5 with 4 candidates, three segments)
  at 270: failed. Early checks at 270: `009-pilot-deckcross-w` (the deck-free board encoder, warm-started) and
  `009-pilot-memgru` both run on. `009x-pilot-exit-strong` (expert iteration) started in the freed slot.
- **Evidence:** 008a answer key 0.745 against the main line's 0.723 (+0.023, rule 0.03); pilot gate −23.0 Elo [−34.6,
  −11.4] after 2,000 games, clearly worse; best decks' Pokémon / Trainers / Energy 17.8 / 12.1 / 30.2 against the main
  line's 17.9 / 17.3 / 24.8; staples 3.42 / 3.17. The warm start of deckcross-w (2,000 games of the main line at 260, 3
  epochs, about 9 minutes): held-out KL 0.106, agreement 0.822, value MSE 0.014. Its first segment: +36.6 Elo [6.7,
  67.1] after 400 games (the deck-blind start of #98: −54.3 at the same point). memgru: −10.3 [−22.3, 1.8] after 2,000
  games, neither clearly worse nor better.
- **Found:** (1) In this form, practising a deck's draws before they count made neither a more human deck nor a better
  pilot. The practised line's best decks stayed Energy-heavy while the main line's reached 17 Trainers. Its pilot fell
  23 Elo behind, plausibly because a season holds each deck's draws fixed, so the pilot plays fewer distinct decks
  (not verified). The heavy variant (season 10) is decided at 280. (2) With the handicap removed, the deck-free
  encoder is ahead after one segment, so Evan's architecture idea is now the strongest pilot result of the day.
  Two more segments decide it.
- **Next:** 008b and memgru at 280, deckcross-w at 290, expert iteration (strong) at 290.

### #101 · 2026-10-19 · A5 · Practice in seasons of 10 passes its answer-key rule but drafts further from the human shape: held for Evan
- **Done:** At 280 the lab decided `008b-meta-practice10` (Evan's practice idea, seasons of 10 with 2 candidates, four
  segments) by its rule: passed. The lab would have adopted it at the end of that decision pass. I stopped the lab
  (taskkill of its process tree) before the adoption, marked the card `passed-held` with a note and an event `held`,
  and restarted the lab at 21:15. Nothing was adopted. The decisions still in progress at 280 (memgru, expert
  iteration's early check) are redone after the restart. deckcross-w's early check had been saved. The 280 milestone
  is the first with the competence score.
- **Evidence:** 008b at 280: answer key 0.766 against the main line's 0.717 (+0.049, rule 0.03), pilot gate −3.3 Elo
  [−15.2, 8.6] after 2,000 games; staples 3.67 / 3.25; best overlap 0.483 both, no archetype at half. Best decks'
  Pokémon / Trainers / Energy: branch 19.2 / 10.3 / 30.4, main line 15.4 / 19.3 / 25.2, the human lists 13.5 / 28 / 18.
  deckcross-w at 280: +20.9 [0.8, 41.1] after 800 games. Milestone at 280: answer key under pilot-v2 0.464 (best 0.621),
  under SimpleBot 0.616, staples 3.25, best overlap 0.483, the main pilot on its own decks against SimpleBot 0.926;
  competence 0.480 (search 0.430, disrupt 0.460, tempo 0.369, attack-won 0.939, Trainer-first 0.577, PlusPower
  0.5625).
- **Found:** (1) The card's rule (answer key only) was written before the plan, which reads drafting cards on deck shape
  too and does not trust the answer key while the pilot misplays Trainers. By Evan's ground-truth rule the card moves
  the wrong way: its decks keep 10 Trainers and 30 Energy while the main line's best decks reached 19 / 25. Meta cards
  need a deck-shape condition in their rule. (2) The main line's competence rose from 0.437 at 260 to 0.480 at 280, almost
  all in the 16 PlusPower puzzles (6 → 9 solved), within about twice the A/A spread; the Trainer-value groups did not
  move.
- **Next:** Evan's call on 008b; a deck-shape condition for meta cards (the distance of the best decks from the human
  medians, with an A/A spread); deckcross-w and expert iteration at 290.

### #102 · 2026-10-19 · A5 · Meta cards gated on deck shape
- **Done:** `rl/lab.py meta_metrics` reports `shape` (the best decks' mean Pokémon / Trainers / Energy) and `shape_dist`
  (its L1 distance from the archived lists' medians 13.5 / 28 / 18, in cards). A meta card now passes only if, beside its
  rule and the pilot gate, its best decks move no more than `shape_max_loss` cards further from the human shape than the
  main line's (`shape_loss` in the rung), as the plan reads drafting cards on deck shape too (#101). The bar comes from the
  A/A cards' evaluations at 160 (`lab.json aa_shape`). It was set after 008b's result, so it does not decide 008b. It
  applies from the lab's next restart.
- **Evidence:** shape distance at 160: main 29.7 (22.1 / 13.4 / 24.5), 001-aa-same 40.2 (21.2 / 8.2 / 30.6),
  002-aa-reseed 33.2 (20.9 / 11.7 / 27.4); differences +10.5 and +3.5, RMS 7.83, bar 16. At 270: main 21.8, 008a 32.3
  (+10.5). At 280: main 17.8, 008b 35.8 (+18.0). `rl.tests` PASS.
- **Found:** Deck shape drifts by up to 10 cards between forks in one segment, so only large shape moves can be read from
  one card. The main line's own shape distance has fallen from 29.7 at 160 to 17.8 at 280.
- **Next:** Evan's call on 008b; the gate on future meta cards (Stage 2).

### #103 · 2026-10-19 · A4 · Expert iteration at full weight teaches Trainers-first unconditionally and loses 79 Elo; less myopic targets
- **Done:** At 280 the lab stopped `009x-pilot-exit-strong` (expert iteration at weight 1.0, a quarter of recorded
  decisions searched, 8 options, 4 lines, one-turn horizon, prize term 0.1) after its first segment, and recorded
  `009-pilot-memgru` as an error. memgru's competence score cannot be computed because a memory pilot has no ONNX export
  for the puzzles (#76), but its Elo gate was clearly worse anyway. `009x-pilot-exit`, `010-pilot-ent02` and
  `010-pilot-lamturn` started at 280. To see why the strong variant lost, I measured its competence and instrumented the
  search: `tsearch` now returns each probe's option keys, and `rl/metagame.py` logs the kind of move (verb) of the
  search's target and of the move played where they differ (`search.verbs`). Also new: a line horizon,
  `--search-horizon H` (`env/runner.js` stops a line once the game turn has advanced H turns; 1 is the end of the turn,
  2 is after the opponent's reply). Queued `009x-pilot-exit-h2` (weight 0.3, 10% of decisions, 2 a game, 6 options, 4
  lines, horizon 2, margin 0.15; decided on competence).
- **Evidence:** exit-strong at 280: −78.6 Elo [−114.3, −44.5] after 400 games; competence 0.442 against the main line's
  0.480 (Trainer-first puzzles 0.680 / 0.577, attack-won 0.886 / 0.939, PlusPower 0.313 / 0.563, search 0.390 / 0.430,
  disrupt 0.443 / 0.460, tempo 0.383 / 0.369). memgru at 280: −21.2 [−34.2, −8.3] after 2,000 games. One-iteration
  forks from `seg_0280.pt` with 200 games, all recorded. At exit-strong's settings: 797 probes, 688 targets, 431
  differing from the move played, target / played verbs trainer 160 / 82, attach 134 / 158, basic 32 / 94, attack 37 /
  55, pass 45 / 35, retreat 13 / 0. At horizon 2, margin 0.15, 6 options, 4 lines: 411 targets, 250 differing, trainer
  75 / 63, attach 79 / 86, basic 21 / 55, attack 33 / 27, pass 30 / 10, retreat 8 / 0, 14,696 lines in 42 s, 0 errors.
- **Found:** (1) Distilling the one-turn search did teach the pilot to play Trainers first (+10 points on those
  puzzles in one segment), but unconditionally. Scored by a weak value at the end of the turn, the search favours
  immediate plays (Trainers, retreating) over development (benching Pokémon), and at weight 1.0 the policy followed it
  and lost 79 Elo. Play-time search solved the puzzles because their wins are terminal and need no value. (2) A
  two-turn horizon and a margin halve the targets and shrink the Trainer lean, but the search still benches less and
  passes more than the pilot; whether the remaining targets help is what exit-h2 measures. (3) All three of Evan's
  memory forms are negative (history tokens −0.016 competence, the attention memory −18 Elo, the GRU −21 Elo).
- **Next:** exit (weight 0.3, one-turn) and lamturn and ent02 at 290–300; exit-h2 when a slot frees; deckcross-w at 290.

### #104 · 2026-10-19 · A4 / A5 · The lab died with its session; two settings races fixed; the deck-free encoder's population reaches 28 Trainers
- **Done:** Found the lab stopped at 22:10. Its last event was the main line's segment to 290 (21:35), and
  `009-pilot-deckcross-w` had stopped at iteration 284 (21:44). There was no error in `lab.stderr.log`, and the PC had not
  rebooted (last boot 10-14). The lab process had been started from a session's shell at 21:15, and it died with that
  session. New: `rl/lab.py start` starts `rl.lab run` in the background outside the shell's job object
  (`CREATE_BREAKAWAY_FROM_JOB`, no console window, defaults `RL_GPU_SHARE` 0.333 and `RL_CPU_THREADS` 10, logs appended).
  Also found: `runs/lab/lab.json` had `s1_min_gain` 0.03 and no `aa_s1` record, though #96 set 0.06. `adopt()` saved the
  settings dict that the lab had read at the start of its cycle, so the adoption of `006-meta-margin0-n` at 14:53 wrote
  back the stale copy over the bar set at about 14:42. No decision depended on it. hist4's gain of −0.016 fails either bar,
  memgru ended in an error, and exit-strong was stopped by its Elo test. The decision pass had the same race for cards:
  it decides from card copies read before that cycle's branch runs (up to about 80 minutes), so a hand edit made
  meanwhile would be ignored and then overwritten. Fixes: `adopt()` merges the settings on disk before it changes and
  saves them, and the due cards are reloaded from disk before they are decided. Restored `s1_min_gain` 0.06 with an
  `aa_s1` record (the #96 numbers). Lifted the hold on `009-pilot-deckcross-w` (`hold_lifted` in the card, event
  `hold-lifted`). The hold kept the practice cards' control while they ran, and both are now decided. So, as its
  hypothesis says, the card is adopted if it passes at 290. Restarted with `rl.lab start` at 22:13 and again at 22:15,
  after the card fix.
- **Evidence:** `rl.tests` PASS (29 s), before and after the card fix. The deck-free pilot exports to ONNX: `warm.pt` of
  deckcross-w (`deck_mode cross`) solves 331 of the 408 puzzles (81.1%; the main line at 220: 79.2%, #96), so its
  competence score can be computed. Shape distance from the human medians 13.5 / 28 / 18 (L1, cards), read from each run's
  per-iteration line (the whole population's median, and the mean of the 3 decks with the best population win rates):

  | | 240 | 260 | 270 | 280 | 285–289 |
  |---|---|---|---|---|---|
  | main line, median P / T / E | 17 / 7 / 36 (42.5) | 17 / 12 / 30 (31.5) | 17 / 18 / 25 (20.5) | 15 / 20 / 25 (16.5) | 14 / 22 / 24 (12.5) |
  | main line, best 3 | 38.5 | 29.2 | 18.5 | 16.5 | 15.8 |
  | deckcross-w, median | – | 16 / 14 / 30 (28.5) | 10 / 26 / 23 (10.5) | 10 / 28 / 21 (6.5) | – |
  | deckcross-w, best 3 | – | 26.5 | 11.5 | 11.5 | – |

  The memgru branch went 17 / 13 / 30 → 17 / 19 / 24 (260 → 278) and 008b 17 / 7 / 36 → 17 / 9 / 34 (250 → 277).
  Before 240 the main line's median Trainers swung between 3 and 15 (150–245), and the result-only reward's replication
  branch fell to 6–7 Trainers (230–235) before it was adopted.
- **Found:** (1) The lab dies with the session that started it, and hand edits to its settings or cards while it runs
  could be silently lost. Both are fixed. (2) Since 240 the main line has made its longest and steadiest move toward the
  human shape (median Trainers 7 → 22, shape distance 42.5 → 12.5). Given its earlier swings and the result-only branch's
  own fall, it cannot be credited to the adopted reward without a test. (3) The deck-free encoder's population
  reached the human median Trainer count (28) by 280, 10 cards closer to the human shape than the main line at the same
  iteration. That gap is about one A/A shape drift (up to 10.5 in a segment, #102), so it is not yet evidence for the
  architecture. The population medians are not best decks under a common pilot, and the answer key was not measured.
- **Next:** At 290, deckcross-w's last segment (adopted if not clearly worse) and the first checks of exit, ent02 and
  lamturn (rebased if deckcross-w is adopted). Then the shape and answer key of the adopted line at the 320 milestone.
  Evan's call on 008b is still open.

### #105 · 2026-10-19 · A4 · At 290: the deck-free board encoder (Evan's idea) adopted; expert iteration at weight 0.3 and turn-level credit fail
- **Done:** The lab decided its four cards at 290 and adopted `009-pilot-deckcross-w`. That is Evan's 10-13 idea: a
  board encoder that never sees the deck, then cross-attention to a separate deck encoder. It was warm-started (#98) and
  ran three segments under a noninferiority test. The main line now goes on from that branch, with its pilot and its
  population. The main checkpoint's config is `deck_mode cross`, and the earlier state was kept as
  `seg_0290.before-009-pilot-deckcross-w.pt`. Stopped after their first segment: `009x-pilot-exit` (expert iteration at
  weight 0.3, one-turn lines) and `010-pilot-lamturn` (λ = 1 inside a turn). `010-pilot-ent02` passed its first check and was
  rebased as `010-pilot-ent02-b`. Started at 290 on the new main line: `009x-pilot-exit-h2`, `010-pilot-ent02-b`,
  `010-pilot-shapeon` and `031-pilot-slotbind`.
- **Evidence:** deckcross-w at 290: +34.9 Elo [15.8, 54.1] against the main line's pilot on drafted decks, after 800
  games (H1); the archived gate +5.4 [−11.6, 22.4] after 1,104 games, not worse. Its three readings were +36.6, +20.9 and
  +34.9. exit: −56.1 [−89.4, −23.8] after 400 games. In its last iterations about 1,000 probes an iteration gave 935–997
  targets, and 570–655 of them differed from the move played. Distillation cross-entropy at 289 was 1.34, with 45%
  agreement. Its PPO, against the main line's at 289: policy entropy 0.99 / 0.72, KL 0.026 / 0.015, clip fraction 0.21 / 0.13.
  Target / played verbs at 289: trainer 167 / 188, attach 215 / 210, basic 87 / 83, attack 58 / 58, pass 90 / 80,
  retreat 27 / 24. lamturn: −37.1 [−56.1, −18.3] after 800 games. ent02: +8.7 [−11.1, 28.5] after 800 games.
- **Found:** (1) Evan's deck-free encoder, given a fair start, is the first architecture change the lab has adopted for
  strength. It led on all three readings, by 21–37 Elo, and was even on the human lists. The population it carries into
  the main line has a median of 10 / 29 / 21 Pokémon / Trainers / Energy (#104), so the main line's decks now start from
  near the human Trainer count. (2) At weight 0.3 with 2 lines a probe, the one-turn search no longer leans to Trainers.
  Its targets disagree with the pilot 60% of the time and look close to noise (the verb counts nearly match those of the
  moves played). Distilling them broadened the policy (entropy +0.27) and cost 56 Elo, so noisy targets are the problem at this
  weight. The two-turn variant uses 4 lines and a margin of 0.15. (3) λ = 1 inside a turn is worse (−37 Elo), as λ = 1
  overall was (#73).
- **Next:** At 300, the first checks of exit-h2, ent02-b, shapeon and slotbind (slot binding grown onto the deck-free
  pilot). At 320, the milestone: competence, deck shape and the answer key of the adopted line.

### #106 · 2026-10-20 · A4 · At 300: expert iteration fails a third time, as do lasting shaping and grown slot binding; lethal-only targets too rare; a deeper pilot queued
- **Done:** These are the lab's first decisions on the deck-free main line. At 300 it stopped three cards after their
  first segment: `009x-pilot-exit-h2` (two-turn lines, 4 a probe, margin 0.15, weight 0.3), `010-pilot-shapeon` (prize
  shaping that never fades) and `031-pilot-slotbind` (slot binding grown onto the deck-free pilot).
  `010-pilot-ent02-b` (entropy 0.02) runs on to its decision at 310, and `032-pilot-lr2` (learning rate 2e-4) started at 300.
  Tried, outside the lab, expert iteration with exact targets: `rl/metagame.py --search-lethal` sets a target only where
  an option won the game in every line, which uses no value. That is the played option if it is one of them. To keep it
  exact, `env/remote_worker.js tsearch` now reports `won`, each option's count of lines that won outright, because a
  stopped line's tanh value can round to 1. A one-iteration fork of `seg_0300.pt` had too few targets to queue as a card.
  Then the larger change from the stall rule (`notes/plan-lab.md`), a bigger pilot. `load_grown` now grows encoder
  blocks beyond the checkpoint's as the identity, with their attention and MLP outputs at 0 (`DEEPER_ZERO`). Queued
  `012-pilot-deep6` and `012-pilot-deep8` (`--pilot-opts {"layers": 6 / 8}`), three segments each, decided on the
  competence score.
- **Evidence:** exit-h2: −36.6 Elo [−62.8, −10.9] after 400 games. At 299 its search made 962 probes, 670 targets and
  463 different from the move played (17,876 lines in 29 s). The distillation cross-entropy was 1.51, with 37%
  agreement. Policy entropy 0.90 against the main line's 0.61, clip fraction 0.17 / 0.11. Target / played verbs:
  trainer 149 / 138, attach 124 / 124, basic 84 / 75, pass 69 / 78, attack 29 / 40. shapeon: −31.4 [−50.3, −12.6] after
  800 games. slotbind: −201.4 [−245.7, −162.4] after 400 games. ent02-b: −14.1 [−26.7, −1.5] after 2,000 games, neither
  verdict. Lethal-only smoke (200 games, all recorded, distill 1.0, 30% of decisions, 6 a game, 8 options, 4 lines):
  1,194 probes, 24,704 lines in 38 s, **1 target**, the same as the move played. `rl.tests` PASS with a deeper-pilot
  check: 2 → 4 blocks, joint and cross, logits and value unchanged within 1e-5. Smoke forks of `seg_0300.pt`, 200 games
  on 2 workers, plain against 6 layers: PPO 29.9 / 42.1 s, total 60.9 / 67.9 s; first-update KL 0.0091 / 0.0100,
  clip fraction 0.075 / 0.084. The main line's first deck-free segment took 21.1 minutes (16.8 before), and its median
  deck held at 10 / 29 / 20 through 290–299.
- **Found:** (1) Expert iteration has failed in all three forms (−79, −56, −37 Elo). Each time, the targets disagreed with
  the pilot on 60–70% of probes, and distilling them made the policy more random (entropy +0.27 and +0.29). So the search's
  scores, a few re-dealt lines scored by the pilot's value, are too noisy to teach from. Exact targets, which need no
  value, are too rare at random probes: 1 in 1,194, since a win within the turn is available only at a game's end.
  Stage 1 step 2 is closed as far as distillation goes. Play-time search still works and stays a tool for evaluation.
  (2) The rest of Stage 1 step 3 is also negative: λ = 1 inside a turn (−37) and lasting shaping (−31). Entropy 0.02
  is the last card in it. (3) Slot binding cannot be grown onto a pilot without breaking its play, as it changes the
  attached-Energy count inputs (#83). Like the deck-blind start of #98, its −201 tests the handicap, not the idea; a
  warm start would test the idea. (4) So the competence gap (Trainer setup) has not been moved by any
  training-signal change. The untested lever is capacity, which #25 flagged as the token model's limit.
- **Next:** ent02-b and lr2 at 310, deep6 and deep8 from 310 (first checks at 320, decisions at 340). The 320
  milestone's scorecard on the deck-free line.
