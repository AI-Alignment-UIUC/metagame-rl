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
