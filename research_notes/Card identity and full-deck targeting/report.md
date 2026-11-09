# Card identity and full-deck targeting (Computer Search)

2026-10-27. This combines three surveys (the code path, card representation, prior work), two literature rounds, and three designs with their critiques. Nothing was built or launched. Most measurements come from one checkpoint (C49-sd 199 = `ar/data/start.pt`) on small samples: 12 deck searches from C94 and 188 fetches from C49-sd's own rollouts. Treat them as one-checkpoint facts, not replicated results.

I re-read the cited lines of `rl/token_model.py` and `env/tokens.js` and log #337-#343, and counted the Trainers' feature rows myself. Everything else comes from the surveys. The probe scripts are in the session scratchpad and may not persist, for example:
- `C:/Users/evanc/AppData/Local/Temp/claude/C--Users-evanc-Desktop-333/997ee0f3-3557-45d7-b1a0-2e33071c249b/scratchpad/cs_probe.py`
- `C:/Users/evanc/AppData/Local/Temp/claude/C--Users-evanc-Desktop-333/997ee0f3-3557-45d7-b1a0-2e33071c249b/scratchpad/cs_bind.py`
- `C:/Users/evanc/AppData/Local/Temp/claude/C--Users-evanc-Desktop-333/997ee0f3-3557-45d7-b1a0-2e33071c249b/scratchpad/c87_init.py`

## Bottom line

- **Card ids are global.**
  - A pick option's id comes from `card(name) = this.cardId.get(name) || 0` (`env/tokens.js:303`), using one table built from `notes/data/cards/pool.json` (`:72-74`).
  - A deck-search option is the row `[pick_card, id, 0, 0, 0, 0]` (`:336`).
  - Across 245 prompts, 117 names map one-to-one onto 117 ids (log #337).
  - So "the ID will refer to a different card in a different deck" does not happen here.
  - The id already indexes the printed card's content: `card_emb = card_resid + Linear(features) + Linear(frozen MiniLM text)` (`rl/token_model.py:395-401`). Every zone token (`:424`) and every option (`:606`) uses it.
- **The real gaps are binding and scale, not ID versus content.**
  - An option never reads its own card's token. A fetch option's attention on its own PROMPT token is 1.01x that on any other (n=188).
  - Permuting copy counts moves the fetch policy by TV 0.009; permuting card ids moves it by 0.967. The search is a near-fixed ranking of card ids.
  - Card identity is a small part of each token. The zone, count and verb embeddings keep their default initialisation (norm about 16), against 2.6 for a Trainer's card_emb.
  - So the same card in hand and in the search listing has cosine 0.46, while Computer Search and Item Finder in hand have 0.999.
  - "One representation per card, shared by every zone" is the part of Evan's direction the model actually lacks.
- **The payoff ceiling is modest.** Oracle answers (capped at 8) lift Computer Search's price by +0.050 (SE about 0.018), to 0.46, still under a basic Energy (C98 condition 3, #341-#342). The rest of the deficit is timing; C99 is recorded but not run.
- **C87's null on key 1 did not test binding.** Its scalar gate ended at -0.021, while PPO's learning went into the static per-card terms (card_resid moved 39% of its norm).
- **Ranked proposals:**
  - P1, Evan's strongest form: each option finds its card by cross-attention over content embeddings, with the card dominating each token, no per-id vector, and a warm start.
  - P2, his minimal variant: key 1 opened from a zero projection, on picks only, with inputs centred within the decision.
  - P3: an effect-prediction auxiliary that gives the binding path a dense signal.
  - A CPU-only gate, Step 0, comes first.
- **What the tests can show.** 30-minute screens read mechanism and harm. Only 110 iterations × 2 seeds reads the price, and even that resolves only about +0.03.

## 1. What the code does today

### Computer Search, end to end

- **Engine** (`ryuu-play/.../set-base/computer-search.js:8-35`). The card runs as printed:
  1. Discard 2 from hand (min = max = 2, cancel allowed).
  2. Computer Search and the 2 discards go to the discard pile.
  3. Choose 1 card from the whole deck (not secret).
  4. Shuffle. The env answers the shuffle itself (`env/legal.js:598`, `env/game.js:307-308`).
- **Options.**
  - There is one `pick|<fullName>` option per distinct name; copies are collapsed (`env/legal.js:309-333`).
  - Picks are made one at a time. The forced `done` is played without asking (`env/runner.js:111-113`), and the no-op cancel is filtered out (`env/game.js:206-216`).
  - A fetch offers 18-31 options (C94 mean 24.0, n=12; A1 mean 23.4, n=16).
  - Nothing is truncated silently: MAX_CAND 128, MAX_TOK 256 (`env/tokens.js:42-43`).
- **What the pilot sees.**
  - At the main phase and the discard step, the deck appears only as MY_UNSEEN: the decklist minus the seat's visible cards, with deck and prizes pooled and aux = copies, capped at 31 (`env/tokens.js:158-170`).
  - During the search, the listing appears as PROMPT tokens with exact deck counts (`:200-207`).
  - Nothing hidden leaks: only the deciding seat is encoded (`env/env.js:48`), and the opponent's prompt answers are hidden (`env/tokens.js:237`).
- **Model** (start.pt config: deck_mode cross, history 0, count_features off, cand_self 0, card_inputs all; no cand_latent, canon or key).
  - Option vector = `cand_in(verb + card_emb(X) + slot_ref + slot_ref + name + extra) + pooled`, then one cross-attention over all tokens, then an MLP score (`rl/token_model.py:605-638`).
  - `slot_ref` binds board slots 1-12 only (`:592-597`). Gust and the Energy Removals are bound to their target's board token (#340); hand, prompt and deck picks are not.

### Card representation

- `card_emb(id)` = `card_resid(id)` (learned, zero-initialised, always on, `:200-204`) + `card_struct(107 features)` + `card_text(frozen 384-d MiniLM)` (`:395-401`).
- The table is `notes/data/cards/pool.json`: 277 cards (225 Pokemon, 42 Trainers, 10 Energy), built from the engine's definitions by `env/tools/card_features.js` (74a3f7b). It holds no human lists or strategy.
- A state token = card_emb + kind(zone) + aux(count or slot) (`:424`).

### Blind spots

1. **No option-to-token binding.**
   - A fetch option puts 0.0208 attention on its own PROMPT token, against 0.0206 on another (ratio 1.01, n=188, C49-sd rollouts).
   - Dropping the option's own token moves its logit by 0.025, against 0.020 for the other options. The own option moved more in only 38% of 288 pairs.
   - Fetch-option queries have cosine 0.959 within a decision.
   - Only `cand_latent` ties an option to its token (`card_tokens()`, `:561-573`), and it is off.
2. **Card identity is drowned out by zone and count.**
   - kind, aux, verb, slot_other, name and extra keep N(0,1) initialisation (`:205-206`, `:304-318`), norm about 16. card_emb has norm 2.6 for Trainers, 3.3 for Energy and 5.5 for Pokemon.
   - Input cosines: Computer Search vs Item Finder, both in hand, 0.999. Computer Search in hand vs as a PROMPT token, 0.462. The same card as PROMPT x1 vs x2, 0.490.
   - count_features is off, so counts are unrelated random vectors (`:205-210`).
3. **Trainers have no structural identity.**
   - Checked today on `card_feature_matrix`: 40 of the 42 Trainers share one structured-feature row, and the other 2 share a second.
   - Telling Trainers apart rests on the MiniLM text (Computer Search vs Item Finder 0.81, vs Energy Search 0.81) and the per-id residual.
   - In the trained card_emb, Computer Search's nearest neighbours are Item Finder (0.935) and The Boss's Way (0.914).
4. **Identity survives, but in a low-variance subspace.**
   - A linear probe decodes the card id from encoder outputs at 97.4% on PROMPT, 98.6% on MY_UNSEEN and 90.9% on HAND.
   - Nearest-centroid decoding gets only 17%, 5% and 14%.
   - Two PROMPT outputs in one state have cosine 0.82. The same card's PROMPT and MY_UNSEEN outputs have cosine 0.22, against 0.07 for different cards.
5. **Fetch, discard and recover share one row, `[11, X, 0, 0, 0, 0]`.**
   - They differ only by a 32-bucket hash of the prompt message (`env/tokens.js:195-199`): bucket 28 for the discard, 31 for the fetch. Each bucket is shared with other Trainers.
   - No token names Computer Search as the card being resolved (history 0, canon off).
6. **The deck stream is board-blind.**
   - MY_UNSEEN and OPP_DECKLIST go through a 1-layer encoder that never sees the board. The fuse updates only board tokens (`rl/token_model.py:244-247`, `:468-481`).
   - state_key can't reach the deck tokens.
   - state_canon moves the listing onto those tokens, pools deck and prizes, and caps the count at 31. Its source flag 128 lands on a second Computer Search still in hand (`env/tokens.js:202-206`, `:221-227`).
7. **Options are scored independently** (cand_self 0). The 18-31 fetch options never see each other.
8. **The discard pair is two sequential picks, then a forced done** (`env/legal.js:261-307`). This is not a credit bug: with per-step baselines the two advantages sum to the pair's (A1 + A2 = Q(s,a1,a2) - V(s)), and with gamma 1, lambda 0.95 they share most of their credit.
9. **Evaluation.**
   - Every fetch the oracle saw was capped at 8 of about 24 answers: C94 12/12, A1 16/16 (`env/tools/probe_target_worker.js:276-283`). The 8 are the greedy answer, the taken answer and random draws.
   - So "+0.080 best answer" is the best of about a third of the deck. A new pilot's changed answers are covered only by chance.
   - Minor: the oracle's 'full' copy tier checks the deck's length, not its contents (10 of 3,072 copies; `:89-111`).
   - Side bug: the `env/game.js:261-264` chain regex ends in `|`, so every action deep-clones the state. This only costs speed.

**What the pilot fetches** (measured).
- On its own decks (188 fetches), its argmax never took an Energy: 104 Pokemon, 84 Trainers. Most frequent: Energy Removal 28, Bill 25, Revive 12.
- On C94's 12 searches, Energy options got 0.01 of the probability mass while being 20% of the options. Mean top probability was 0.79.

## 2. What was tried, and why it doesn't settle the question

| Attempt | Budget | Result | Why it doesn't settle it |
|---|---|---|---|
| Shared content vocabulary (card_emb) | in since A4 | standard design | Drowned out by token scale (blind spot 2); Trainers share features (3) |
| slot_bind, cand_self, deck-cross, deck-inter (#71-#74) | 40 iterations, 1 seed, Elo | within noise (seed noise 6.5-19.5 Elo) | Never read on prompts or X1; all predate the pick-order fix (#235) |
| Deck-free encoder (#98-#105); slot_bind grown cold (#106) | lab | adopted after a warm start; cold starts lost -54 and -201 Elo | Changes that don't start as the identity need a warm start |
| Evan's keys 1-4 (ar rows 37-40) | 5 min, 1 seed each | lat1 0.4589, lat2 0.4755, state_key 0.4669, canon 0.4574 (A/A 0.454, bar 0.4784) | Too short to read; C80 never ran; lat2 never got seed 2 |
| C87, key 1 (#286) | 110 iterations, 1 seed, 61,809 games | M 0.4658 vs 0.4655; X1 +0.010 (SE 0.009); replay dG -0.0021 (0.0037); Computer Search +0.008 (0.008) | Path suppressed (see below); Computer Search was about 5% of probes |
| X1 / X10 (#241) | 72,462 prompts (20,940 Computer Search) | Random answers tie the pilot's (search group -0.001, SE 0.013); permuting Trainer inputs -0.401 | X10 wasn't measured at the fetch. The new probe is: id-permute TV 0.967 |
| C83 / C88 / C89, C79 / C81, history | various | null or failed | A signal of about 0.02 per decision needs about 8,000 paired playouts |
| C95 (#333-#338) | quarantined | ridge rho_dis 0.294 / 0.223; no candidate beats the pilot | At most 8 answers; CIs about ±0.4 |
| C98 (#338-#342) | 2 seeds | price 0.443 replicates; untimed 0.40; oracle answers +0.050, to 0.46 | Sets the ceiling |

**C87, corrected.** The critique rebuilt C87's seed-1 init and found:
- lat_proj did train. It moved 1.23 (cosine 0.991 to its init), about as much as cand_in (1.12) and the score head (1.33).
- What it learned is one rank-1 spike: top singular value 1.356, against 1.13-1.16 for random matrices. That is most likely the shared "names a card" offset.
- g_lat ended at -0.021. Adam moves a scalar at most about the LR (2e-4) per step, so this is about 105 steps of net drift. The path carried about 1% of the option vector.
- PPO learned through the static per-card terms instead: card_resid moved 3.86 (39% of its norm) and card_text 3.47.

Read this way, C87 is a null on "a gated extra path under PPO", not on binding. The earlier "lat_proj barely moved" reading is wrong.

**Never run:**
- the H55 card-input ablation
- a card_resid ablation
- a full-deck fetch oracle
- the Computer Search price under a card-token pilot
- an action-conditioned dynamics loss (row64-spr, 7fdb95f, is pooled-only and never ran)
- cand_latent_kinds
- row64-optpot

## 3. What the literature suggests

The survey agents read these sources; I did not re-read them. Items marked *(memory)* were not read.

- **On a fixed pool, card encoding barely matters.**
  - Bertram et al., CoG 2024 (arXiv 2407.05879, Table II): seen cards one-hot 67.80%, random 67.87%, features+text 67.76%.
  - Unseen sets: random 23.79%, features+text 33.57%.
  - So content over id is a transfer feature (MTG, new sets), not a fix for Computer Search.
- **Pointing at the entity's own encoded token is the standard pattern.**
  - ygo-agent (code read) gathers `f_cards[B, spec_index]`, with frozen text in the id table.
  - OpenAI Five (arXiv 1912.06680, App. H) uses target attention with a per-action key mask.
  - AlphaStar's unit heads point over entity embeddings (secondary read). Its joint log-probability for multi-pick actions is *(memory)*.
  - UPDeT (arXiv 2101.08001) is the only controlled result: breaking the action-entity pairing falls below a GRU baseline. That comparison is against pooled baselines, which the pilot already beats.
- **Credit under sparse reward.**
  - Wolpertinger (arXiv 1512.07679): critic re-ranking was essential; k=1 failed.
  - Chandak 2019 (arXiv 1902.00183) learns action representations from P(a|s,s') with no reward, for up to 2-3x returns.
  - Jain 2020 (arXiv 2011.01928): subsampled action sets plus entropy.
  - AGILE (abstract only): attention among the available actions.
  - Kool 2019 (arXiv 1803.08475): a same-instance rollout baseline gave a 0.34% gap vs 0.96% with a learned critic.
- **Effect prediction as a dense signal.**
  - Cardsformer (abstract and code) predicts next-state stats from card text.
  - Xia et al., AAMAS 2025 (full text) uses a latent transition loss: 96/76/68% vs Cardsformer's 82/68/48% against tree-search levels.
  - Its GPT-4 deck summaries are a human prior, so only the transition loss is usable here.
- **Multisets.** Gerigk & Engels (AIIDE 2023, Dominion) encode MLP(card + multiplicity) with DeepSets and model multi-select as single picks.
- **Warnings.**
  - EMMA (arXiv 2101.07393): learning from reward alone conflates similar descriptions. Computer Search vs Item Finder text cosine is 0.81.
  - Tucker 2018 *(memory)*: baseline gains are often implementation details.
  - A Slay the Spire blog (low confidence): id embeddings fit human picks best but played worst.
- **Ruled out by the project's rules:** human pick data, meta statistics, Forge AI hints, HearthArena *(memory)*, GPT-4 deck summaries.

## 4. Ranked proposals

### Shared protocol

- **Start and runs.**
  - start.pt, seeds 1 and 2, 9 iterations (`fixed.ITERS`).
  - One arm per ar/ worktree through `ar_milestone.py`; the arms run sequentially, since it refuses above 4000 MiB (`:112`).
- **Evaluation settings.**
  - M uses C87's settings (`--eval-seed 1091 --guard-seed 1097 --eval-games 64`).
  - The price uses C97's harness (`trainer_value.py --decks archived --games 64 --round-turns 20-45 --seed 91 --groups "Computer Search"`).
- **Control and reference points.**
  - Control C: plain ar/train.py, same seeds. Reuse the A/A pilots at 99904d5 if they were saved; otherwise train C once and share it across all arms.
  - T0: each arm after any init or distillation, before PPO. Mechanism metrics are read as T - T0, against C - start.
- **Noise.**
  - The per-pilot price SE is about 0.011, so a difference has an SE of about 0.016.
  - Across three seeds of the A/A runs at 9 iterations, M varies by 0.032.
  - So screens read mechanism and harm only; the price is reported, not banded.
- **Harm guard.**
  - Loss if M(T) - M(C) <= -0.02 at both seeds, or price D <= -0.03 at both seeds.
  - Skip seed 2 if seed 1 shows M <= -0.04 or D <= -0.05.
- **Kill rules:** errors above 1%, a crash or ONNX failure, KL above 0.05 for 2 iterations, entropy below 0.5x C's, `runs/GPU-PAUSE`, or 35 minutes per block.
- **Promotion** (needs Evan's OK).
  - 110 iterations × 2 seeds, about 75 minutes per seed per arm, or chained 30-minute segments.
  - Bands: D >= +0.025 at both seeds is a gain; |mean D| < 0.01 is null; <= -0.025 is a loss.
  - X1 on the search group counts as a gain if G-U >= +0.03 and above 2 SE at both seeds.
  - Use 128 games a list for the price (SE about 0.008, an estimate).
- **Evaluation-only:** the oracle, ridge probes and human lists are never trained on.
- **Timings** are estimates. Time a 1-iteration pilot first.

### Step 0: gate (CPU only, no training, about 20 minutes)

**(a) Does the own-token latent add value?**
- Data: the frozen start pilot on the Computer Search prompts of C94 and A1 (about 80 decisions).
- C95's ridge, with nested 5-fold CV by game, both fit seeds, and a paired bootstrap.
- Four feature sets:
  1. [emb]
  2. [emb + L_own centred within the decision]
  3. [emb + count one-hot]
  4. [emb + centred L_own with counts shuffled]

**(b) How much does play rely on the per-id vector?** Zero card_resid in start.pt (no retraining) and price M and Computer Search.

**Change:** a `--feat` option in `qhead_testbed.py` plus a run-folder script, about 25-40 lines. c1r/c2r on B need L recomputed for its 1,619 prompts.

| Reading | Condition | Then |
|---|---|---|
| L adds value | Δrho_dis(L) >= +0.10, CI above 0, at both fit seeds | P2, then P1 |
| It's the count | Δcount within 0.05 of ΔL, and ΔL with counts shuffled < +0.05 | P2 variant (c) first |
| Null | every \|Δ\| < 0.05 | P2 gets one screen; P1 runs only as a transfer design |
| Unreadable (my prior) | otherwise | P2 |
| (b) relies on the id vector | M drops >= 0.02 | supports P1's warm-started removal |
| (b) content suffices | M drops < 0.01 | P1 piece 2 is cosmetic here |

### P1: Evan's strongest form, cards reached by cross-attention over content

**Mechanism:**
1. **`cand_latent 3`: content-keyed cross-attention.**
   - The query is the centred, normalised content of X plus the verb. The keys are each state token's card content, and the values are the encoder outputs.
   - `card_tokens()`'s zone logic sets the mask.
   - The temperature is set so the own card gets at least 0.95 of the attention at init; content vectors are unique (rank 278/278).
   - The result replaces `card_emb(X)` in the option (`:606`), with no gate and no static term.
2. **`card_content=1`.** Fold card_resid into the content maps by least squares, then drop it. On this pool that is capacity-neutral (492 columns for 278 cards); its payoff is transfer.
3. **`emb_scale`.** Shrink the kind, aux, verb, slot_other, name and extra embeddings, and turn on `count_features` (`:207-210`), so the card dominates every token and counts are ordinal.
4. **Origin code.** Put the source zone (hand, deck or discard) in a free field of the pick row (`env/tokens.js:336`), read by a zero-initialised embedding.

**Warm start:** distil to start.pt with `rl/warmstart.py` (#98), on the agent's own states.

**Change (about 150 lines):**
- `token_model.py`: about 110 lines.
- `tokens.js`: about 5.
- `tests.py`: about 20.
- A loader adapter: about 15.

Pause ar; it needs a new `--setup` and `--calibrate` afterwards.

**How it differs from the null keys:**
- Key 1 kept the static card term, and its gate stayed shut.
- Key 2 was zero-gated.
- state_key can't reach the deck stream, and canon moves the listing onto board-blind tokens.
- None of them fixed token scale or counts, or matched by content.

**Test:** two 30-minute blocks.
- Block 1: gates, distillation and T0 readouts.
- Block 2: T at seeds 1 and 2.

| Readout | Pass | Otherwise |
|---|---|---|
| Fold max error | < 1e-4 | kill |
| Own-card attention mass at init | >= 0.95 | kill |
| Swap two listed PROMPT tokens' outputs; T0's logits follow their tokens | >= 90% of pairs | kill |
| HAND vs PROMPT cosine for one card (start 0.46); two Trainers in hand (start 0.999) | >= 0.8; <= 0.9 | report |
| T0 vs start: TV; argmax agreement | <= 0.03; >= 0.95 | kill |
| M(T0) - M(start) | >= -0.02 | kill |
| Count-shuffle TV on fetches, T - T0 (start 0.009) | >= +0.03 at both seeds, with C - start <= 0.01 | null |
| Energy-fetch mass, price D, X1 | report (a lean if D >= +0.02 at both seeds) | |

**Promotion:** promote if all gates pass, the harm guard holds and the count band passes.

**Main risk: drift across the main phase.** HAND tokens decode identity at only 90.9%, and the fetch payoff is capped at +0.05. Other risks: 9 iterations may leave the path "wired, not yet learned"; the learned temperature may blur Computer Search with Item Finder.

### P2: Evan's minimal variant, key 1 opened and narrowed

**Mechanism:**
- Key 1 (C87's zone and gate), with lat_proj's weight and bias set to 0 and g_lat fixed at 1 and frozen.
- So step 0 is bit-identical to start.pt, and lat_proj gets its full gradient from step 1.
- Picks only (verbs 11-15).
- L centred within the decision.
- Canon off, so a fetch reads its own PROMPT token, which carries the exact count.
- card_resid is left alone: freezing it alone would just move learning to card_text, which C87 also moved by 3.47.

**Variants:**
- (b) Key 2 on picks only, with ptr_q zero-initialised and g_ptr fixed at 1. Check that its step-0 TV is <= 0.001. Key 2 had the best single seed (0.4755) and never got a second.
- (c) A zero-initialised count embedding on pick rows, if Step 0 reads "it's the count".

**Change:** `token_model.py` about 12 lines (`cand_latent_pick`, `cand_latent_center`), `ar/train.py` about 6, and a probe script of about 30.

**How it differs from C87:** no scalar gate, picks only, and centred L.

**Test:** one 30-minute block. Variant (b) gets its own block.

| Readout | Pass | Otherwise |
|---|---|---|
| Logits bit-identical on C94's 245 prompts; lat_proj gradient nonzero | must hold | kill |
| Path ratio \|\|W·L_c\|\| / \|\|embed\|\| on fetches at iteration 9 (C87 about 0.01) | >= 0.05 | kill at iteration 5 if < 0.01 |
| \|cos\| of W's top direction with mean L | < 0.5 | C87 repeat |
| Path logit sd / logit sd within a fetch | >= 0.10 at both seeds | null if < 0.03 |
| Latent-shuffle TV (T0 = 0) | >= 0.05 | null |
| Price, X1, replay dG with coverage | report | |

These rows show the path is live and card-specific, not that it helps.

**Main risk:** about 1,700 fetches per arm (an estimate) may be too few for PPO to learn what counts are worth. A pass with no outcome gain points to P3.

### P3: option-conditioned effect prediction (Claude's addition; only after P1 or P2 passes)

**Mechanism:**
- A small head P reads the chosen option's final vector and predicts the stop-gradient change in its own card's tokens by the same seat's next decision in the same turn, minus the per-verb mean.
- That gives about 37k labels an iteration, against about 190 fetches. For a fetch the label is deterministic.
- It is never in the policy loss and uses no reward, oracle or human data. It finishes row64-spr (7fdb95f).
- It must sit on P1, or on P2 with the static card term dropped from pick rows. Otherwise P can bypass the token.

**Change:** `ar/train.py`, about 50 lines:
- port `next_rows()` and the target pass from 7fdb95f
- a graph-keeping hook on `model.score`
- P's own Adam
- a separate backward and clip, so the shared 0.5 clip doesn't shrink PPO's step
- logged gradient norms

**Test:** one block, the same arm with and without the auxiliary, at both seeds.

| Readout | Pass | Otherwise |
|---|---|---|
| Held-out NMSE on fetch rows vs a pooled+verb predictor | >= 10% lower by iteration 9 | kill at iteration 5 if there is no gap |
| Target norm | drops < 50% | kill |
| Aux/PPO gradient-norm ratio | <= 1 | retune |
| Count-shuffle TV and logit spread vs the arm without it | >= +0.02 at both seeds | null |

**Main risk:** option-blind auxiliary heads (#84, #88) cost Elo, and this teaches effects, not preferences.

### Dropped or demoted

- **Pair credit:** already unbiased. Joining the picks adds V2 - V1 noise and changes Item Finder and Energy Retrieval game-wide.
- **The standalone content fold:** an exact reparametrisation on this pool.
- **Afterstate re-ranking.**
  - It ranks the oracle's answers at rho +0.35 [0.12, 0.54], n=12, but its argmax is worse than greedy (+0.011 vs +0.047), and it counts as planning.
  - The "6 of 28 fetches were Energy" note was chance (5.2 vs 5.5 expected).
  - `C:/Users/evanc/AppData/Local/Temp/claude/C--Users-evanc-Desktop-333/997ee0f3-3557-45d7-b1a0-2e33071c249b/scratchpad/cs_fetch_best.py` has superType off by one.
- **Canon for the fetch** puts the listing on board-blind tokens and pools the prizes.
- **Per-instance deck tokens:** no evidence they help.
- **C95 re-embedding and C94's capped stratum** are no longer primary readouts.

### Evaluation fixes needed regardless

- **A full-deck fetch oracle**, needed before any promotion read.
  - It needs a stored-state entry for `probe_target_signal.py`.
  - Cost: about 37k rollouts, 15 minutes or more.
  - At m 128 the SE is about 0.044, so it can rank groups of answers, not the single best one.
- Report deck searches as their own stratum.
- Optional: fix the copy-tier contents check and the chain-regex speed bug.
- In `notes/evan-requests.md`, rows 89-90: strongest form = P1, variant = P2, both "not tried".

## 5. Open questions for Evan (defaults in brackets)

1. **Ids are already global, and on a fixed 277-card pool content versus id doesn't change capacity** (67.80% vs 67.76% on seen cards). Content pays off for unseen cards (MTG) and for sharing between similar cards; the real gap here is binding and scale. Build P1 anyway? [Yes. Run P2 first and build P1 while it runs.]
2. **The price needs 110 iterations × 2 seeds per arm** (about 5 hours for T and C), and that only resolves about +0.025-0.03 against a +0.05 ceiling. OK to run it as chained 30-minute segments for a design that passes its screen? [Yes, one design at a time.]
3. **Oracle answers leave Computer Search at 0.46; the rest is timing.** Run C99 (#343) alongside? [Yes, it is evaluation only.]
4. **Leave the discard pair's credit as it is?** [Yes.]
5. **Is P3, a self-supervised loss on engine transitions, within your rules?** [Yes, after the P1 or P2 gates pass.]
6. **Afterstate scoring is decision-time planning.** Keep it off? [Off.]

**Run order** [default]: Step 0, then P2 and its key-2 variant, then P1 (built in parallel), then P3.
