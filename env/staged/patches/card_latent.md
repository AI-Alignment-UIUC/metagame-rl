# card_latent: options read the encoder latent of the card they name (Evan's rows 65-66)

Patch `card_latent.patch` (from 77fbae0; rl/token_model.py, rl/gpu_matrix.py, rl/train.py; about 65 lines), design in `reports/Unified card token references.md` (A). Three keys, default 0; the config records them only when `cand_latent` is on, so old checkpoints and configs are untouched.
- `cand_latent` 1: per option, L = mean of x over the state tokens with the option's card id (card != 0, not padding), added as `g_lat * lat_proj(L)` to the candidate vector before `cand_in`. `g_lat` is a scalar starting at 0; `lat_proj` keeps default init. Chain rows get it too (same `embed`).
- `cand_latent` 2 (variant): `g_ptr * log(softmax mass)` added to the option's logit; `ptr_q(final candidate vector)` is scored against all tokens, mass is summed over the matching ones (0 added when none match, log clamped at -14). `g_ptr` starts at 0.
- `cand_latent_zone` 1: keep only tokens of the option's source zone. HAND for slot 14 or the attach / basic / evolve / trainer verbs (these play from the hand with no slot code, so slot 14 alone would miss them: my addition), MY_DISCARD for slot 15, PROMPT for pick verbs 11-15, else all zones; all matches if the zone holds none.
- `cand_latent_gate` 1: `L *= sigmoid(lat_verb(verb_emb) + 4)` per dimension.
Callers: `forward()` passes tok_card and tok_kind to `heads()` (new trailing kwargs; notes/scripts/memory_reach.py calls heads() without them, fine while the keys are off). Registered in build_token_model (via kwargs), gpu_matrix.load_policy (also allows the new names as missing weights), train.build_model / token_net / NEW_WEIGHTS (so warmstart, lab, metagame, evaluate_agents grow checkpoints). ar/fixed.start_model needs no change: it calls load_policy.

MODEL_OVERRIDES (ar/train.py):
    {"cand_latent": 1, "cand_latent_zone": 1, "cand_latent_gate": 1}     # strongest
    {"cand_latent": 2, "cand_latent_zone": 1}                            # variant
Cost: one [B,C,T]x[B,T,d] matmul plus a d x d Linear (and a second d x d for the gate) per candidate pass; key 2 adds one B x C x T score. Estimate under 1% of FLOPs, not timed. ONNX export not run.

Tests (`test_card_latent.py`, CPU, 1111 real decisions from C49-sd self-play incl. 1651 chain rows): (a) off: state_dict keys, config and outputs equal to an unpatched tree, with and without chain; (b) g = 0 bit-identical for four key combinations, chain 0 and 4; (c) g = 1 changes logits at all 144 card-naming pick rows and gives nonzero gradients to g_lat, lat_proj, lat_verb (g_ptr, ptr_q for key 2); (d) zone resolution 97.0% (pick, 494 candidates) and 100% (hand, 4241 candidates); (e) C49-sd loads with the overrides, step-0 logits, values and greedy actions identical.
