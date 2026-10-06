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
