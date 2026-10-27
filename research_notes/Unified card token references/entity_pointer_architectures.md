# Entity-centric RL: actions that point at the encoder's latent for an entity

Scope note: about 14 tool calls. The AlphaStar Nature paper and supplement were NOT retrievable; AlphaStar facts below come from AlphaStar Unplugged (same architecture family, DeepMind) and secondary text. Nothing was verified against the DeepMind code.

## 1. AlphaStar: entity encoder and pointer heads

### Takeaway
AlphaStar's selected-units and target-unit heads are pointer networks over the entity transformer's per-unit outputs, so an action refers to a unit through the encoder's latent for it. I found no published ablation of pointing at latents versus static embeddings.

### Cited Findings
- Architecture (Unplugged, a re-implementation by the same group): MLP for vector inputs, transformer for the units input; seven arguments sampled autoregressively (function, delay, queued, repeat, unit_tags, target_unit_tag, world); unit_tags and target_unit_tag "refer to indices in the units inputs" and are sampled with pointer networks from the vector and units modalities; unit_tags is 64 autoregressive pointer samples. — [AlphaStar Unplugged](https://arxiv.org/pdf/2308.03526)
- Entity encoder: transformer, 3 layers, 2 heads, d=128, up to 512 entities; output is pooled into a state summary and also used per-unit by the pointer network. — [Perceiver IO paper describing AlphaStar](https://arxiv.org/pdf/2107.14795); [TStarBot-X reuses this transformer and target pointer](https://arxiv.org/pdf/2011.13729)
- Memory ablation in Unplugged: no memory beat LSTM for behaviour cloning; a transformer memory beat memory-less only at 2x training frames. (Consistent with this project's memory variants being within noise.) — [AlphaStar Unplugged sec. 5.6](https://arxiv.org/pdf/2308.03526)
- Other StarCraft agents copy the pattern: target head = compatibility of an action embedding (query) with entity embeddings (keys), with invalid-target handling; selected-units head adds sequential selection. — [TacticCraft](https://arxiv.org/pdf/2507.15618). A cyber-defence entity-RL paper does the same (query from acting entity, key per candidate entity, dot product), no head ablation. — [Entity-based RL for cyber defence](https://arxiv.org/pdf/2410.17647)

### Inferences
- Pointer-over-latents is the default for variable entity sets; the literature gives no evidence for or against it versus static embedding plus attention.
- The pilot already has the query side (candidate embedding cross-attends to the tokens). What it lacks is a key bound to the specific entity: a hand/deck/prompt-card candidate sees only card_emb(card) and must recover which token it is by content-based attention.

### Gaps
- AlphaStar Nature supplement (key construction, any pointer ablation) not read. Check the pseudocode at github.com/deepmind/alphastar.

Loop change: config key `cand_latent: 0|1` (default 0). In heads(), per candidate compute m = (tok_card[:,None,:] == card[:,:,None]) & ~pad (optionally AND a zone filter, see section 4), L = (m @ x) / m.sum(-1).clamp(min=1); then c = c + alpha_lat * Linear(L), alpha_lat a scalar parameter init 0 (section 5). Needs tok_card passed into heads(). Cost: one B x C x T matmul and one d x d Linear, under 1% of FLOPs. Test: warm-start from the 290 checkpoint, assert logits identical at step 0, train on the Trainer-prompt choice metric (#241; lookahead headroom +0.044) against a control, 3 seeds.

## 2. OpenAI Five: unit embeddings and target selection

### Takeaway
Five points at unit embeddings taken from the observation encoder ("process set"), carried beside the LSTM, with a dot-product attention head whose keys are masked by a learned per-action mask. No ablation of the head is reported.

### Cited Findings
- Unit Embeddings are taken from the "embedding output" of each unit's process-set and "carried along beside the LSTM, and used by the action heads to choose a unit to target." — [OpenAI Five, Appendix, Figs 17-18](https://arxiv.org/pdf/1912.06680)
- Head: primary action = linear projection over available actions; target unit = attention (dot product, softmax) of an LSTM-derived query over unit keys, "masked by a learned per-action mask based on the sampled action" (sigmoid, multiplied onto keys). — same source
- The ablations in the paper concern reward weights, scale and data quality, not the target head. — same source

### Inferences
- The per-action key mask is a verb-conditioned gate on the entity key: the same entity is scored differently per verb. Analogue here: gate the card latent by the verb embedding, which separates "discard X" from "fetch X".

### Gaps
- No ablation of pointing versus alternatives.

Loop change: config key `cand_latent_gate: 0|1`, on top of cand_latent: L <- L * sigmoid(Wv(verb_emb) + 4) (bias +4 starts the gate near 1; alpha_lat still starts the path at 0). Cost: one d x d Linear. Test: against ungated cand_latent.

## 3. Entity transformers in MARL (UPDeT, REFIL), MicroRTS, others

### Takeaway
The one controlled result: in UPDeT, breaking the pairing between the attack action and the enemy entity collapses performance below the GRU baseline, so action outputs must be tied to the right entity's output.

### Cited Findings
- UPDeT: a transformer cannot emit more outputs than inputs, so the action space is split into action-groups, each paired with one observation-entity; each entity's output token maps through a shared FC to its action group; entities with no actions are dropped. — [UPDeT](https://arxiv.org/pdf/2101.08001)
- UPDeT ablation: disrupting the attack-action to enemy-entity correspondence "heavily decreased" performance, "even worse than the GRU-based model". About 80% gain over GRU on 4m vs 5m (Hard+) with VDN. Self-reported; no independent replication found. — same source, Sec. 4.1
- REFIL (ICML 2021): entity-attention agents for variable entity counts plus an auxiliary randomized entity-subset value factorization; the reported gains come from the auxiliary objective, not an action head. — [REFIL, PMLR](https://proceedings.mlr.press/v139/iqbal21a.html)
- Gym-microRTS: GridNet vs unit-action-simulation is about action decomposition and masking (a full action mask matters far more than a partial one); it is not an entity-pointer vs grid comparison. — [Gym-microRTS](https://arxiv.org/pdf/2105.13807)

### Inferences
- UPDeT shows binding matters; it permutes the pairing, not the latent source, so it does not show latent beats static embedding.
- A binding failure is a plausible cause of the pilot's chance-level Trainer-prompt choices: a candidate with only card_emb cannot name "this prompt-list token".

### Gaps
- Neural MMO and Hanabi: nothing usable found; do not cite. No REFIL action-head ablation found.

Loop change: cand_latent (section 1) is the UPDeT pairing realised by card-id matching. Add an eval diagnostic: shuffle L across candidates in a batch; if choice quality drops below the alpha=0 model, the path is used. Cost: eval only.

## 4. Pointer networks, Kool et al., and duplicates: which instance's latent?

### Takeaway
Pointer and attention decoders point at encoder node embeddings (Vinyals; Kool). For duplicates, the copy-mechanism convention sums attention mass over all matching positions; entity RL systems sidestep it with one index per entity.

### Cited Findings
- Kool et al.: attention-layer model that improves on the Pointer Network, trained with REINFORCE and a greedy-rollout baseline; near-optimal TSP up to 100 nodes. Only the abstract was read. — [Kool et al.](https://arxiv.org/abs/1803.08475)
- Copy mechanisms sum attention weights over every input position holding the same token: p(w) = sum over {i: x_i = w} of alpha_i. — [DeepCopy](https://arxiv.org/pdf/1908.10731)

### Inferences
- AlphaStar, UPDeT and Five appear to index entities one-to-one, so duplicates do not arise (inferred from the descriptions, not stated).
- Here the pilot already merges copies into one token per distinct card per zone (aux = count), so "which copy" is moot; the real question is which zone's token. A candidate knows its source from its verb/prompt, so a zone filter helps: prompt-list candidates match the prompt kind, hand plays match hand. With no filter, a mean over all matches is the safe default; it is order-invariant and Magic-portable.

### Gaps
- Kool decoder details (context node, glimpse, clipped pointer) are from memory, not read; not needed for the change.

Loop change: config key `cand_latent_kinds: "all"|"learned"`. "learned" uses a weight w[verb, kind] (init 1 = mean over every matching token), applied as m * softplus-normalised weights. Cost: n_verbs x n_kinds floats. Test: "all" vs "learned"; log which kinds each verb learns, a diagnostic for the unified vocabulary.

## 5. Adding the pathway without losing play

### Takeaway
Put a zero-initialised scalar gate on the new residual branch (ReZero) so the warm-started network is exactly the old function at step 0 and the pathway grows only if the gradient asks for it.

### Cited Findings
- ReZero: gate each residual connection with a single zero-initialised parameter; trains thousands of FC layers with fast convergence, 120-layer transformers, and 12-layer transformers on enwiki8 converge 56% faster; satisfies initial dynamical isometry. — [ReZero](https://arxiv.org/abs/2003.04887)
- Fixup (zero-init the last layer of residual branches plus scalar multipliers) is the similar identity-start trick; from memory, not fetched.

### Inferences
- With alpha = 0 and the Linear at normal init, the gradient on alpha is nonzero, so it trains. Zeroing both alpha and the Linear weights gives zero gradient to both (dead path): zero only one.
- The repo already uses this idiom (per-card residual and agent embedding start at zero, see the token_model.py docstring), so it fits house style.

### Gaps
- No study found on warm-starting entity pointer heads in RL; ReZero's evidence is for deep supervised nets.

Loop change: one residual `c = c + alpha_lat * proj(L)` with alpha_lat = nn.Parameter(0.). New keys go in self.cfg with default 0 so old checkpoints load (missing weights fresh-init). Test: load the 290 checkpoint with cand_latent=1, assert max |logits_new - logits_old| < 1e-6 on saved states, then train; kill early if the Trainer-prompt metric is flat after the first short budget.

## Ranked changes
1. cand_latent (id-match gather of the encoder output, zero-init gate): cheapest, most direct reading of Evan's request.
2. cand_latent_gate (verb-conditioned, from Five's per-action key mask).
3. cand_latent_kinds (learned verb-to-zone weights).

Caveat: slot binding was already within noise (#71-#74, #76-#103), and that path binds board slots, which already had latents. Hand/deck/prompt cards are the untested case, but the literature has no ablation promising a gain, so the expected effect is unknown.
