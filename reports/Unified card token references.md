# Pointing options at card latents, behind zero gates

Build one thing first: let a card-naming option read the encoder's latent for the matching state token (hand, discard, prompt list, deck), instead of only the static `card_emb`. ygo-agent is the only open card-game agent found that does this, and AlphaStar and OpenAI Five use the same pattern for unit targets. No paper ablates "point at the latent" against "re-embed statically", so the literature gives precedent but not a promised gain. The repo's own evidence (X1: Trainer prompt answers are random; C73: lookahead answers worth +0.044, SE 0.008, one seed) says the gap exists, and the test is cheap. The design below is six opt-in keys, default off and bit-identical when off. Four of them (the action-side gather and its variant, the state-side merge and its variant) are the A/B pairs Evan asked for. Evan's rule applies: each idea gets its strongest version plus a variant, and both are logged as tried or not tried.

## What others do, and how strong the evidence is

| System | Mechanism | Evidence strength |
|---|---|---|
| ygo-agent | One row per card instance, zone as an additive embedding. Each action holds a card index, gathers the post-encoder latent `f_cards[B, spec_index]`, and cross-attends to the card tokens ([README](https://github.com/sbl1996/ygo-agent), [agent.py](https://raw.githubusercontent.com/sbl1996/ygo-agent/main/ygoai/rl/agent.py)) | Architecture only, no ablation. Its README lists unseen-card generalisation as roadmap |
| AlphaStar | Unit-selection heads are pointer networks over the entity transformer's per-unit outputs ([Unplugged](https://arxiv.org/pdf/2308.03526), [Perceiver IO](https://arxiv.org/pdf/2107.14795)) | Architecture only. The Nature supplement was not retrieved |
| OpenAI Five | Target unit = dot-product attention over unit embeddings, keys masked by a learned per-action mask ([Appendix](https://arxiv.org/pdf/1912.06680)) | Architecture only. Ablations cover other things |
| UPDeT | Each entity's output token maps to its own action group. Breaking the attack-to-enemy pairing drops performance below the GRU baseline ([UPDeT](https://arxiv.org/pdf/2101.08001)) | The only controlled result, and it shows binding matters, not that a latent beats a static embedding. Self-reported |
| DraftFM, Cardsformer, T5 follow-up | Frozen text embeddings as the shared card vocabulary, which transfers to unseen sets or decks ([DraftFM](https://arxiv.org/pdf/2608.19568), [AAMAS 2025](https://aamas.csc.liv.ac.uk/Proceedings/aamas2025/pdfs/p2795.pdf)) | Good for the vocabulary, which `card_emb` already has. None describes pointer targets |
| Object-centric RL | Attention readout beats pooling: MLP pooling dropped Object Interaction from 0.787 to 0.03, and a single vector fails at 3 objects ([Yoon 2023](https://arxiv.org/html/2302.04419)) | Pixel tasks, so transfer is by analogy. Supports a per-token identity key |

Two cautions. First, the "unified vocabulary" mostly exists: `card_emb` is already shared by every state token and every option. What is unshared is the latent. Second, duplicates are not a problem here, because tokens are one per distinct card per zone. The real question is which zone's token an option points at, and the copy-mechanism convention of summing mass over matches ([DeepCopy](https://arxiv.org/pdf/1908.10731)) answers it when the zone is ambiguous.

## (A) Actions: gather the matching token's latent

All A keys are read in `heads()`, need `tok_card` and `tok_kind` passed in, and leave board slots 1-12 unchanged. Defaults are 0, and the off path skips the new code.

| Key | Values | Semantics | Init | Cost (estimate) |
|---|---|---|---|---|
| `cand_latent` | 0 / 1 / 2 | 1 (strongest) = gather. For each candidate, `m = (tok_card == card) & kind_ok & ~pad`, `L = (m @ x) / m.sum.clamp(1)`, then `c += g_lat * Linear(L)` before `cand_in`. 2 (variant) = pointer logit. Add `g_ptr * log(mass on matched tokens)`, where mass is the softmax of the candidate query over token keys summed over `m`. Same matching, but it acts on the score, not the candidate vector | `g_lat`, `g_ptr` scalar = 0, Linear and keys at default init (zeroing both kills the gradient) | one B x C x T matmul plus one d x d Linear, under 1% FLOPs |
| `cand_latent_zone` | 0 / 1 | 1 = `kind_ok` from the option's source: hand play -> HAND, discard (slot 14/15) -> MY_DISCARD, prompt pick -> PROMPT, deck search -> PROMPT, else MY_UNSEEN. 0 = mean over all matching tokens. Soft fallback to "all" when no token matches | none | nothing |
| `cand_latent_gate` | 0 / 1 | `L *= sigmoid(Wv(verb_emb) + 4)`, Five's per-action key mask. The same card is read differently for "discard X" and "fetch X" | bias +4 starts near 1, and `g_lat` still holds the path at 0 | one d x d Linear |

Strongest version: `cand_latent=1, cand_latent_zone=1, cand_latent_gate=1`. Variant: `cand_latent=2` with zone matching. I avoid a hard mask on matches because KG-A2C's graph mask helped on 10 games and hurt on 6 ([Ammanabrolu & Hausknecht](https://arxiv.org/pdf/2001.08837)). The zone filter is a soft-fallback filter, and all-zone mean is the default-off fallback.

Needs in `env/tokens.js`: a per-candidate zone code, one int, flag-gated. It is derivable from the existing slot refs 13/14/15 plus prompt context, so first check whether `token_model.py` can infer it without a JS change. Without that code, only the all-zone mean is possible.

## (B) State: make the same card one thing across zones

| Key | Semantics | Identity start? | Needs |
|---|---|---|---|
| `state_canon` (strongest) | One canonical token per distinct card per zone. Prompt-listed, picked and source become flag embeddings (3 learned vectors, each scaled by a zero-init scalar) added to the zone token. A deck-search listing merges into the MY_UNSEEN token, a discard listing into MY_DISCARD, a pick into the token it came from. PROMPT/PICKED kinds disappear | **No.** Merging changes the token set, so it cannot be bit-identical to the old model when on. Off stays bit-identical. Test it as a fine-tune from the C49-sd start | `env/tokens.js`: merge on build and emit flag bits in `aux`/new fields. `token_model.py`: flag embeddings. About 30-50 lines in JS (estimate) |
| `state_key` (lighter variant) | Per-head scalar attention bias added to every token pair with the same card id in different zones, so attention can bind them. Same mechanism as the `slot_bind` same-slot bias | Yes, bias = 0 | `token_model.py` only, O(T^2) mask |

The caution on `state_key`: `card_emb` is already added to every token, so identity is already readable by content, and slot binding was within noise (#71-#103). Expect little from `state_key`. `state_canon` is the version that matters, because it gives A a single, unambiguous token to point at, which is why A's `cand_latent_zone` and B pair up. Already planned and not duplicated here: the SOURCE token as a PROMPT-kind token with aux 0 (tonight's deploy).

Chain rows (this turn's earlier decisions) go through the same candidate path, so they inherit A for free if they fill `card` and the zone code. Their referent is the PICKED token today and the flagged zone token under `state_canon`. Check that chain rows set the zone code to the original referent's kind, not a new "chain" kind, or the gather finds nothing.

## Tests, in order

1. **Step-0 bit-identity**: with every gate at 0, assert `max |logits_new - logits_old| < 1e-6` on saved states, off path exactly identical. Applies to `cand_latent`, the zone and gate keys, and `state_key`. Not to `state_canon`.
2. **X1 re-run** (random vs pilot prompt answers inside Trainers) as the mechanism readout. Success is a pilot-minus-random gap clearly above zero, moving toward the lookahead headroom of +0.044. This is the test that can be read at 5 minutes, because the M signal cannot: single-seed 5-minute runs are about 1 sd (A1), and A4 found nothing moves M in 5 minutes.
3. **M at 20 minutes x 3 seeds** against the shared baseline, with the weaker-play guard. Only keys that pass step 1 and show an X1 gain go here. Kill early if X1 is flat after the first budget (Evan's stop rule).
4. **Latent-shuffle diagnostic**: at eval, shuffle `L` across candidates in a batch. If choice quality does not fall toward the `g=0` model, the path is unused. Also log `|g|` and, with `cand_latent_zone`, which kinds each verb matches.

## Order for ar/ideas.md

| # | Idea | MODEL_OVERRIDES (key syntax to confirm against the config) |
|---|---|---|
| 1 | A strongest: gated gather, zone-aware, verb-gated | `{"cand_latent": 1, "cand_latent_zone": 1, "cand_latent_gate": 1}` |
| 2 | A variant: pointer logit | `{"cand_latent": 2, "cand_latent_zone": 1}` |
| 3 | B strongest: canonical tokens with flags (fine-tune, not identity start) | `{"state_canon": 1}` |
| 4 | A1 on top of B1 | `{"state_canon": 1, "cand_latent": 1, "cand_latent_zone": 1}` |
| 5 | B variant: identity bias | `{"state_key": 1}` |

Items 1-2 are the single-change A/B and run first, since they need only `token_model.py` if the zone code is inferable. Item 4 runs only if 1 or 3 shows an X1 gain. Item 5 is last because it is the likeliest null.

## Conclusion

The expected effect is unknown, and that is why the order is cheap-first. If the gather moves X1 and not M, the plateau is not an action-reference problem and the next lever is the Trainer's effect model, not the vocabulary. If the shuffle diagnostic shows the path is unused even with a gain in X1, the gain came from extra capacity, not binding.

Source caveat: most arXiv papers were read at abstract level only, and several mechanism details (Gato, Kool, Fixup, ReZero's use here) are from memory. Nothing was checked against the DeepMind code. ReZero ([paper](https://arxiv.org/abs/2003.04887)) is for deep supervised nets, not RL entity heads.
