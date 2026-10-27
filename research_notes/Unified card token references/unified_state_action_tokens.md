# Unified token vocabularies shared by state and actions; actions as pointers into state tokens

Reading: pilot `rl/token_model.py` heads() (lines 481-524) read directly. Candidate c = verb + STATIC card_emb(card) + slot_ref(s1) + slot_ref(s2) + name + extra, then cand_in + pooled, then one cross-attention to x (encoded tokens), then score. slot_ref gathers the ENCODER OUTPUT x only for board slots 1-12; hand/deck/prompt-list cards get only the static embedding, never a contextual latent. This is the gap.
Source-quality caveat: WebFetch returned abstracts only for most arXiv PDFs (PDF text was unreadable), so mechanism details marked "(memory)" are NOT verified in this session.

## 1. Pointer / copy mechanisms: does pointing at contextual latents beat re-embedding the referent?

### Takeaway
Pointer nets, CopyNet and pointer-generator all score outputs by attention over the (contextual) input states, because the output set is the variable input. Strongest direct support: AlphaStar-style unit selection and the entity-pointer head in cyber-defence RL. I found no controlled ablation "pointer into contextual latent vs. re-embed referent" in RL; the evidence is architectural precedent plus indirect results.

### Cited Findings
- Ptr-Net uses attention weights as pointers selecting an input position, for outputs whose class count depends on input length; generalized beyond training input lengths — [Vinyals 2015](https://arxiv.org/abs/1506.03134)
- Pointer-generator copies from source while generating; beats prior abstractive SOTA by >=2 ROUGE on CNN/DM; coverage reduces repetition — [See 2017](https://arxiv.org/abs/1704.04368)
- CopyNet mixes generation with selecting input subsequences to copy; large gains over plain RNN on summarization — [Gu 2016](https://arxiv.org/abs/1603.06393)
- AlphaStar: entity encoder (transformer, 3 layers, 2 heads, dim 128) output is used both pooled as state summary and per-unit; a pointer network over those per-unit representations gives probability of each unit selection; unit arguments sampled by pointer networks — [Perceiver IO describing AlphaStar](https://arxiv.org/pdf/2107.14795); [AlphaStar Unplugged](https://arxiv.org/pdf/2308.03526) (secondary, via search snippets)
- Cyber-defence entity RL: SelectEntity action = dot product of a query from the acting entity with keys from each candidate entity, "similar in function to pointer networks"; plus a dummy "global" entity for non-entity actions — [arXiv 2410.17647](https://arxiv.org/pdf/2410.17647) (search snippet only; PDF unreadable)
- ATM (NeurIPS 2022) binds each action to the environment entity it involves before predicting value/logit, as an action-semantic inductive bias; improved MARL algorithms on SMAC and Level-Based Foraging — [NeurIPS 2022](https://proceedings.neurips.cc/paper_files/paper/2022/hash/e1cf57f1e104c6c05e31894c15a65e99-Abstract.html) (abstract level; no numbers retrieved)
- TStarBot-X replaced sequential selection with a multi-binary selection head over shared unit representations for efficiency and says it "generally works well" — [TStarBot-X](https://arxiv.org/pdf/2011.13729) (snippet)

### Inferences
- Pointing means the logit is a function of the referent's contextual latent. In the pilot, a Trainer-prompt option ("fetch card X from deck") sees only static card_emb(X), so it cannot know what X would do in THIS board/hand context; board-slot options do read x. This asymmetry matches the observed failure (log #241) and is the AlphaStar-style fix: score the referent's encoded token.
- A pointer needs the referent to exist as a token. Deck/prompt-list cards must be encoder tokens (the pilot has deck tokens, deck_tokens=True; verify prompt-list cards are tokens, otherwise add them).

### Gaps
- No RL paper found that ablates pointer-to-latent vs re-embedded referent. The loop's own test is the evidence.

## 2. Generalist/sequence agents: one shared vocabulary for states and actions?

### Takeaway
Gato and Multi-Game DT put heterogeneous inputs and actions in one token sequence/transformer, but this is a sequence-modelling convenience; I found no evidence that sharing a vocabulary for the SAME object (state vs action) is what makes them work. Closest relevant result: per-component action tokens that attend to state (M-SAT).

### Cited Findings
- Gato: one network, one set of weights, outputs "text, joint torques, button presses, or other tokens" — [Reed 2022](https://arxiv.org/abs/2205.06175) (abstract only; tokenization details unread)
- Multi-Game DT: single transformer trained offline plays up to 46 Atari games near human level; performance scales with size — [Lee 2022](https://arxiv.org/abs/2205.15241) (abstract only)
- M-SAT: each action component gets its own token, concatenated with the preceding state embedding; authors argue attention, not the tokeniser, should decide which actions matter. Deadly Corridor 16.17 +/- 0.33 (no PE) vs 12.28 +/- 3.1 for action-only-token MAT; My Way Home 0.964 +/- 0.005 vs 0.747 +/- 0.249; only two ViZDoom envs, limited generality acknowledged — [arXiv 2407.01310](https://arxiv.org/html/2407.01310v1)

### Inferences
- (memory, unverified) Gato/DT action tokens are generated, not pointers to state tokens, so they do not address "refer to the same object". They are weak evidence either way for Evan's idea.
- M-SAT supports grounding action tokens in state embeddings (lower variance), consistent with candidates reading state latents.

### Gaps
- Gato tokenization section, Trajectory Transformer, VPT/MineDojo tokenizers not retrieved (PDFs unreadable, budget).

## 3. Relational / object-centric RL: when shared object latents help

### Takeaway
Self-attention over entities helps relational tasks and generalization; object-centric slots help most when the task is relational/compositional and the readout is attention-based. They do not help on simple tasks.

### Cited Findings
- Relational deep RL: self-attention over scene entities guides a model-free policy; gains in Box-World (sample complexity, generalization) and SOTA on six StarCraft II minigames, above grandmaster on four — [Zambaldi 2018](https://arxiv.org/abs/1806.01830) (abstract only)
- OCR pretraining study: SLATE object representations ~ ground-truth states on Object and Property Comparison and beat single-vector baselines; but on Object Interaction several slot models failed and end-to-end CNN was more sample-efficient; single-vector VAE Object Goal success fell 0.999 -> 0.686 from one to three objects (binding problem) — [Yoon 2023](https://arxiv.org/html/2302.04419)
- Same study: transformer pooling is critical: MLP pooling dropped Object Interaction 0.787 -> 0.03, Property Comparison 0.98 -> 0.229; Deep Sets 0.513, Relational Network 0.150 — [Yoon 2023](https://arxiv.org/html/2302.04419)
- Working Memory Graphs: transformer over observation entities plus memory tokens gives "significant gains in learning efficiency" on Pathfinding, BabyAI, Sokoban — [Loynd 2020](https://arxiv.org/abs/1911.07141) (abstract)
- Entity-centric manipulation from pixels: each entity one token with self-attention — [arXiv 2404.01220](https://arxiv.org/pdf/2404.01220) (snippet)

### Inferences
- The pilot already has the relational encoder. What is missing is the action-side readout: Yoon's pooling result suggests attention-based reads of object latents are decisive; heads() cross-attention is that kind, but the query lacks the referent's latent for off-board cards.
- The binding result (single vector fails with 3 objects) supports a per-token identity key so a card in several zones is recognized as one.

### Gaps
- Yoon is pixel-based; transfer to symbolic tokens is by analogy only.

## 4. Text-adventure / language-action RL: referring to objects by observed tokens

### Takeaway
Language-action agents constrain or fill action slots from entities in the observation, which is pointing; benefit is positive but mixed.

### Cited Findings
- KG-A2C: template action space (~1.15e8 combos, six orders smaller than word-level) with a graph mask limiting object choices to known entities; full beats no-mask on 10 games, loses on 6 — [Ammanabrolu & Hausknecht 2020](https://arxiv.org/pdf/2001.08837) (search snippet; exact slot-fill mechanism not retrieved)
- CALM: language model proposes candidate actions from history, RL agent re-ranks them — [Yao 2020](https://arxiv.org/abs/2010.02903)

### Inferences
- The graph mask is the analogue of restricting a prompt option's pointer to matching tokens. The 10/6 split warns hard masks can hurt; prefer a soft additive bias.

### Gaps
- KG-A2C pointer/slot-fill details not verified.

## 5. Practical design: cards in several zones; identity key

### Takeaway
No paper settles this. Options: (a) gather the exact token when the option names one; (b) a learned card-identity key with a soft match bias in the pointer attention when it is ambiguous.

### Cited Findings
- Dedicated global/null target for non-entity actions — [arXiv 2410.17647](https://arxiv.org/pdf/2410.17647)
- Pointer attention gives a distribution over input positions (multiplicity handled by probability mass) — [Vinyals 2015](https://arxiv.org/abs/1506.03134)

### Inferences (design, uncited)
- The pilot's card_emb is already a shared static vocabulary on state tokens and candidates, so the "unified vocabulary" mostly exists; what is unshared is the LATENT. Use card_emb(card) as the query and add a learned per-head bias for tokens whose card id matches (same mechanism as slot_bind's same-slot bias).
- Multi-zone duplicates: masked mean of x over tokens with the same card id (optionally restricted by kind/zone of the option).

### Gaps
- Need to check env/tokens.js: can each option carry the token index of its referent?

## 6. Warm-start with a zero-init gate

### Takeaway
Standard practice (ReZero/LoRA/ControlNet style, from memory, no citation retrieved): new term = g * path with g=0, so the function is unchanged at step 0 and g still gets gradient.

### Cited Findings
- None retrieved this session.

### Inferences
- Zero the scalar gate but leave the projection default-init (zeroing both stalls learning). Assert step-0 logits are identical to the start pilot.

### Gaps
- No citation.

## Loop change:
Add opt-in flag `ptr_latent` (default False) to TokenPointerNet.heads(): for each option add `g * Proj(pointee_latent)` to c before cand_in, where pointee_latent = x gathered at the option's referent token index (extend slot_ref to hand/deck/prompt-list tokens; if the tokenizer has no per-option token index, add one as a 7th cand field in env/tokens.js; for multi-zone references use a masked mean of x over tokens with the same card id). g is a learned scalar initialised to 0 and Proj keeps default init, so step-0 logits equal the start pilot (unit-test it). Cost: one gather and one Linear(d,d) per forward; the real work is exposing the token index. Test: (1) step-0 logit equality; (2) Trainer-prompt pick quality vs random on the log #241 probe set after a 5-minute `ar/` run; success = clearly above random with M and the weaker-play guard not dropping. Variant: add a pointer logit (dot of option query with token keys, AlphaStar/cyber-defence style) to the score, also gated at 0.
