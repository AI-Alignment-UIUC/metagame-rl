# Card tokenization across zones and actions in card-game agents

Scope: how open card-game agents/models tokenize cards by zone, reference a card inside an action, and keep one card's identity consistent. About 14 tool calls. Several primary papers could only be read as abstracts (marked in Gaps). Statements labelled "(memory)" are from my background knowledge, not a fetched source.

## 1. Yu-Gi-Oh (ygo-agent): the closest open design to a unified card vocabulary with pointer actions

### Takeaway
ygo-agent gives every physical card on the field/hand/GY one row of one table. Zone is a feature on the row (an embedding added to the card vector), and an action refers to a card by an integer index into that same table. The action row is then cross-attended against the encoded card rows. So state and action share one token set and one card embedding.

### Cited Findings
- Observation arrays (uint8): `cards_` 160x41 (per-card feature rows), `global_` 23, `actions_` 24x12 (legal actions), `h_actions_` 32x14 (action history), `mask_`. Embeddings from an LLM over card text are optional (`embed{n}.pkl`); zero-shot generalisation to new cards is listed as roadmap, not delivered. — [ygo-agent README](https://github.com/sbl1996/ygo-agent)
- In `agent.py`: card id (cols 0-1, two bytes -> 16-bit id) indexes a 1000-entry table of 1024-d vectors then an MLP; zone/location (col 2) is a 9-value `loc_embed` added to the card vector; sequence (col 3) is a `seq_embed`; owner, position, overlay, attribute, race, level, counter, negated each get small embeddings; ATK/DEF are 32 soft bins; type flags pass through an MLP. All are summed/concatenated into one card vector, passed through a transformer encoder (`card_net`) with a padding mask; a learned "no-card" token sits at index 0; global features (LP, turn, phase, hand sizes) are added to every card. — [ygo-agent agent.py](https://raw.githubusercontent.com/sbl1996/ygo-agent/main/ygoai/rl/agent.py) (read via WebFetch summary)
- Actions: each row holds a card pointer (`spec_index`, cols 0-1) plus 11 categorical fields (message, action type, yes/no, phase, cancel, finish, position, option, number, place, attribute). `get_action_card_` gathers the referenced card from the ENCODED card table (`f_cards[B, spec_index]`), adds a small MLP residual and the action-feature embedding, then `action_card_net` (TransformerDecoder layers) uses the actions as queries and the card tokens as keys/values. Index 0 is the no-card token, so actions that name no card still work. — same file
- History actions are referenced by content, not pointer: their card id goes through `id_embed` directly, not into the current card table. — same file
- Output: one logit per action, with invalid `msg==0` rows masked to -inf. — same file

### Inferences
- This is the exact pattern Evan describes ("unified vocabulary ... learning latents with attention ... and for referring to them on the game state"): one id->embedding, one set of state tokens carrying zone, and options that point at state tokens (gather the post-attention latent) rather than re-embedding statically. The pilot differs in the last step: its options use `card_emb(card)` statically and only board-slot targets read the latent.
- A pointer can only reach cards that have a state token. In ygo-agent a prompt-listed card is a card on a zone (deck search lists are cards in the deck zone; YGOPro only lists visible cards), so it is already a row. In this repo the PROMPT tokens play that role; an option that is "pick card X from the PROMPT list" should therefore gather the latent of the matching PROMPT token.
- Caveat: ygo-agent's card id embedding is a learned per-id table (1000 entries), so its generalisation to unseen cards is, per its own README, not solved. The unified-pointer part transfers; the vocabulary part is what card_emb() (features + text + residual) already improves.

### Gaps
- I did not read ygo-agent's encoder for how a pending selection (select-cards prompt) is represented beyond the `actions_` columns (message / finish / cancel fields). The README summary does not describe it.
- A "Duel Transformer" paper was not found.

## 2. Hearthstone: Cardsformer and the T5 follow-up (text as the shared card vocabulary)

### Takeaway
Hearthstone agents that generalise to unseen cards do so by encoding card TEXT with a frozen/fine-tuned language encoder and using that vector wherever the card appears (hand, board, deck). The evidence is win rates on decks with up to 50% unseen cards. Neither source I could read describes pointer-style target selection.

### Cited Findings
- Cardsformer (ECAI 2023, Xia et al.): two parts, a Prediction Model trained on offline trajectories to predict state transitions from card descriptions, and a Policy Model that generalises to unseen cards; reported better data efficiency and state of the art including decks with untrained cards; PyStone code released. — [IOS Press abstract](https://ebooks.iospress.nl/doi/10.3233/FAIA230581)
- A search summary says Cardsformer trains Deep Monte-Carlo Q-learning in self-play and uses MPNet sentence embeddings; I could not confirm either from the paper text. — [IOS Press page](https://ebooks.iospress.nl/pdf/doi/10.3233/FAIA230581) (unverified detail)
- AAMAS 2025 extended abstract (Xia, Fang, Guo, Du, Xu): the encoder of a T5-base fine-tuned on a card dataset (card -> description, "each card as a unique token") and a deck-strategy dataset (5,000+ decks summarised by GPT-4); T5 encoder outputs are mean-pooled and L2-normalised as the card/deck representation; a Q-network over representation module (cards + stats), with an auxiliary latent-space transition (world model) loss, trained by self-play Monte Carlo. Five test decks with unseen cards, up to 50% unseen in one; win rates vs tree search level 0/1/2: ours 96/76/68%, Cardsformer 82/68/48%, GPT-4o 60/24/12%. — [AAMAS 2025 PDF](https://aamas.csc.liv.ac.uk/Proceedings/aamas2025/pdfs/p2795.pdf)
- That paper's Q(o,a) is computed on a joint observation+action encoding, h_t = f(o_t, a_t), i.e. the action is another input to the encoder, not a pointer. — same PDF

### Inferences
- The auxiliary transition loss on a text-derived latent is the one Hearthstone idea that targets exactly this repo's problem (the model should know what a Trainer DOES so it can pick the one that helps). Cheap analogue: predict the next-state numeric slice (hand size, prizes) from (state, option) with card_emb as input.
- Text encoder frozen vs fine-tuned: T5 was fine-tuned on card->text generation; DraftFM (below) keeps the sentence encoder frozen and learns an MLP on top. Both work; frozen is simpler.

### Gaps
- Cardsformer full text (state tensor layout, how targets of effects such as attack/spell targets are encoded) was not readable; no arXiv version exists per search. The T5 abstract does not detail target selection either. I found no Hearthstone transformer-agent paper describing hand/board entity tokens with pointer targets.

## 3. Magic: drafting transformers and text embeddings as the shared vocabulary

### Takeaway
For MTG drafting the clear result is that cards represented as feature vectors plus a frozen sentence embedding of rules text transfer to whole unseen expansions; learned per-card vocabulary indices cannot. Pool and pack are handled as sets (shared per-card encoder, count embedding, attention pooling). I found no MTG PLAY agent with documented card/zone/stack tokenization.

### Cited Findings
- DraftFM (Ward, arXiv Aug 2026): each card = 775 numbers (391 structured features, 384 L2-normalised frozen `bge-small-en-v1.5` embedding of type line + rules text, with the card's own name replaced before embedding so it cannot act as an id; reminder text kept). No card-id, set-id or usage features. Shared card encoder 775-512-d. Pool (<=46 distinct cards) = card embedding + learned count embedding (capped at 8), summarised by four learned queries with 4-head cross-attention (closely related to Set Transformer pooling, Lee et al. 2019). Candidate score MLP on [e_i; p; e_i*p; h] with softmax over the K pack cards. 1.6M parameters, 149M picks, 29 expansions; top-1 agreement on three fully held-out expansions 50.8 / 60.4 / 56.7% vs about 7% chance at the opening pick. Prior drafters it cites "encode cards as vocabulary indices" and cannot score an unseen set. — [DraftFM](https://arxiv.org/pdf/2608.19568)
- Same paper: zero-shot GPT-4o agreed with human picks 43% on Kamigawa: Neon Dynasty; its stated lesson is "use a frozen text embedding as a feature, not a language model as the policy". It attributes to Bertram et al. (2024a) that multi-set pretraining, not representation alone, buys transfer. — same PDF
- Learning With Generalised Card Representations for MTG (Bertram et al. 2024): representations from numerical, nominal, text features, images and meta data; the choice matters little for known cards but "performance on new, unseen cards can be greatly improved"; 55% of human choices predicted on completely unseen cards. — [arXiv 2407.05879](https://arxiv.org/abs/2407.05879)
- Contrastive Learning of Preferences with a Contextual InfoNCE Loss embeds card text with BERT and concatenates other features (per search summary). — [arXiv 2407.05898](https://arxiv.org/pdf/2407.05898) (summary only)
- MTG-Causal-RL (da Costa Cunha et al., arXiv 2605.06066, preprint): Gymnasium env, flat 3,077-d partial observation, 478-action masked discrete space, five Standard archetypes; baselines masked PPO and CGFA-PPO. This is a fixed-size flat observation and a fixed action vocabulary; the abstract gives no card-level tokenization. — [arXiv 2605.06066](https://arxiv.org/abs/2605.06066)

### Inferences
- For MTG later, the pilot's structured-features + text-embedding + residual recipe matches the state of the art for transfer. Two DraftFM details worth copying: replace the card's own name in the text before embedding (blocks hidden id leakage, and in this repo makes the text path a purer test of "reads the rules"), and add a learned count embedding to the zone token (the pilot's aux = copies already does this).
- The learned residual is the part that can memorise per-card id; DraftFM drops it entirely and still transfers. If the residual dominates, the pilot may be memorising Trainer ids instead of reading text. Test by weight-decaying or removing it for Trainer options.
- MTG-Causal-RL shows the flat-vector alternative; it is not a model for what Evan wants.

### Gaps
- No documented stack/"pending choice" token, Forge-based RL tokenization, or Draftsim neural model with card tokenization was found. "Puder transformer" (Czerner 2025) and Bertram 2024a are only cited secondhand in DraftFM.

## 4. Pokemon TCG agents (community), pointer heads and the static-option weakness

### Takeaway
Existing PTCG agents are small, deck-specific community projects. Their option scoring is a pointer-style dot product between a board vector and option embeddings, which is the same design as the pilot and has no closer link between an option and its state token.

### Cited Findings
- pkm-cabt-ppo: board embedded to a single vector h; each legal option embedded as o_i; policy = softmax over option scores against h plus a summary of options already picked this decision; multi-select is sequential picks with a learned STOP row legal after minCount picks; card embedding 32-d, ~0.5M parameters; card identity embedded so each checkpoint is tied to one deck; evaluated only vs a random agent, 20 games. — [HF TomatoCream/pkm-cabt-ppo](https://huggingface.co/TomatoCream/pkm-cabt-ppo)
- PTCG MuZero (richard151111): 4-layer, d=256 transformer encoder; card embedding = learned 64-d + 48-d static CSV features; zone/option tokenization not documented on the page. — [HF muzero-V2](https://huggingface.co/richard151111/muzero-V2)
- Master's thesis (AAU 2026) swapped a fixed output layer for a pointer head scoring each candidate by dot product of a learned query with the card embedding; accuracy about 59% unchanged. Domain is card-game imitation, not PTCG RL. — [thesis PDF](https://projekter.aau.dk/projekter/files/822057972/MasterThesis_LT_02_2026.pdf) (via search summary)
- Gwent, Legends of Runeterra: no agent papers found.

### Inferences
- pkm-cabt-ppo's "summary of options already picked" is the same job as the pilot's PICKED tokens, but PICKED tokens are attendable, which is stronger.
- Nobody in this sample conditions an option on its own latent state token, except ygo-agent. That makes ygo-agent the one reference worth copying.

### Gaps
- Unverified: all the HF pages are self-reported; no Elo against strong baselines.

## 5. Instance tokens vs type-per-zone tokens with counts; set encoders; pending-choice token

### Takeaway
The sources show both conventions. ygo-agent uses one token per physical card instance (160 rows, with sequence index). DraftFM uses one token per distinct card with a count embedding. The pilot's type-per-zone + aux=copies matches DraftFM and loses nothing for hidden-identical cards; the cost is that an option cannot name "the second copy", which does not matter for picking a card by identity.

### Cited Findings
- Zone is encoded as an additive embedding on the card row in ygo-agent (`loc_embed`, `seq_embed`); there is no separate per-zone sequence. — [agent.py](https://raw.githubusercontent.com/sbl1996/ygo-agent/main/ygoai/rl/agent.py)
- DraftFM pool = distinct-card set + count embedding, pooled by learned-query cross-attention, "closely related to attention-based models for set-valued inputs" (Set Transformer: Lee et al. 2019). — [DraftFM](https://arxiv.org/pdf/2608.19568); set-transformer paper: [arXiv 1810.00825](https://arxiv.org/abs/1810.00825v1)
- Pointer-network style heads and entity encoders were popularised by AlphaStar (entity transformer then pointer net for unit targets) and Zambaldi et al. relational RL — [Relational Deep RL](https://ar5iv.labs.arxiv.org/html/1806.01830) (relational attention over entities only; the AlphaStar pointer claim is from memory).
- A pending-choice or stack token: in ygo-agent the prompt is conveyed by the message/action-type fields on each action row and global features; I found no separate "pending choice" token in any source. The pilot's PROMPT/PICKED tokens plus a prompt-type one-hot already go further.

### Inferences
- The card that opened the prompt (the Trainer being resolved) has no token in the pilot. In ygo-agent the analogue is the message field naming the effect card via the same card-pointer index, so the resolving card is a card row. Adding it as a token (kind = SOURCE) is consistent with every design above and cheap.
- No source tests instance vs type tokens head-to-head; treat the claim "type tokens suffice" as untested.
- Evidence that text embeddings are the unseen-card vocabulary: DraftFM and Bertram (MTG), Cardsformer/T5 (Hearthstone). Evidence that doing so for play (not drafting) works: only the Hearthstone papers.

### Gaps
- No head-to-head of instance vs count tokens; no paper on set encoders for in-game zones was found.

## Loop change (opt-in, summary)

Each ends with the required line; costs are my estimates, not measured.

1. Loop change: option-to-token pointer (the ygo-agent mechanism). In rl/token_model.py heads(), for every option whose card appears as a state token (PROMPT, PICKED, HAND, MY_DISCARD, deck/UNSEEN zones), add the post-encoder latent of that token (gathered by the option's token index, with index 0 = no-card) to the static card_emb(card) option vector, then let options self- or cross-attend to the encoder output as ygo-agent does with its decoder layers. env/tokens.js must emit, per candidate, the index of its matching token (one extra int, about 3 lines, flag-gated). Cost: one gather plus one small MLP, a few percent of the forward pass; no new data. Test: retrain from the C49-sd start under the same 5-minute `ar/fixed.py` budget, compare the M score and the random-vs-lookahead choice agreement at Trainer prompts (log #241 setup) against the current model; expect agreement to rise only if static embeddings were the bottleneck.
2. Loop change: add a SOURCE token for the card that opened the prompt (the resolving Trainer), kind = new SOURCE, aux = 0, using the same card id so card_emb is shared. Cost: 1 token per decision and one KIND entry in env/tokens.js. Test: A/B on the same Trainer-prompt agreement metric; also check that permuting the source card's identity now hurts more than the current 70 Elo.
3. Loop change: DraftFM-style identity hygiene for the text path: replace each card's own name with a placeholder before embedding its rules text, and run an ablation that zeroes `card_resid` for Trainers. Cost: a one-time re-embedding of the pool, no inference cost. Test: if choice quality at Trainer prompts holds or rises with the residual off, the residual was memorising ids; if the permutation penalty drops, the model was leaning on identity rather than on the text.
4. Loop change (optional, from the Hearthstone T5 paper): an auxiliary next-state prediction head from (option latent, state latent) to a small numeric target (own hand size, prize delta). Cost: one small head and one loss term, flag-gated in the trainer. Test: Trainer-prompt agreement with and without the aux loss at equal steps.
