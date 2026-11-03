# Game-state representation in card-game AIs (for the Pokémon TCG pilot)

Evidence tags: **read** = full page fetched (via WebFetch, which returns a model-written summary of the page, not verbatim text); **snippet** = search-result text only, not opened; **abstract** = arXiv landing page only; **memory** = none used. Sources read: 5 full pages plus 2 abstracts. Snippet-only sources are weak and are marked.

## Key Question 1: What do the Dominion articles encode for state and actions?

### Takeaway
Ian Davis's Dominion series uses a very small state (turn, score difference, Provinces left, purchase counts) and no hand, deck or discard encoding. The main gains came from action masking and from thermometer-style encodings of those few numbers. The deck-composition and draw-probability ideas that matter for this project appear only in a hand-coded heuristic (Cellar).

### Cited Findings
- Part 1 (rules and GA). Six-card reduced Dominion (Copper, Silver, Gold, Estate, Duchy, Province); action cards excluded. The GA ranks buys with 7 weights; the linear-rank GA beats the fixed-rank GA 73 to 66 out of 100 — [Dominion part 1](https://ianwdavis.com/dominion.html) (**read**).
- Part 1, tabular RL. State = turn (capped at 20), score difference to the leading opponent (-13 to +13), Provinces remaining (capped at 3). 763 of 1,620 possible states visited. Hand, deck and discard are not in the state. Head-to-head: RL won 15% at 50k games, 49% at 500k, 53% at 5M — [Dominion part 1](https://ianwdavis.com/dominion.html) (**read**).
- Part 2, state encoding. Initial features `[t/20, s/13, p/3]`. The improved encoding uses "progressively turned-on binary flags": 20 bits for turn, separate positive and negative score bits, 4 bits for Provinces (50 features). Win rate rose from under 20% to about 30%, then to about 40% with the encoding changes and count features — [Dominion part 2](https://ianwdavis.com/dominion2.html) (**read**). The article's own sentence (quoted from the summary) describes the change as "counts represented as progressively turned-on binary flags."
- Part 2, actions. Seven actions (buy each of six cards, or END). Invalid actions are masked by setting logits to -inf before the softmax. Early legality flags as input alone produced only Provinces and Silvers. Masking was "the biggest breakthrough": the agent then learned Big Money and finished in about 18 rounds — [Dominion part 2](https://ianwdavis.com/dominion2.html) (**read**).
- Part 2, network and training. MLP, one 32-unit hidden layer, later two layers of 64 units, Tanh (ReLU did not help). Basic policy gradient, then PPO with a separate value network as baseline. Self-play. Sparse win/loss reward. 400 epochs (about 100k self-play games, about 90 minutes) roughly matched a Monte Carlo model trained on 5M games — [Dominion part 2](https://ianwdavis.com/dominion2.html) (**read**).
- Part 2, what did not help. Doubling or halving the learning rate, ±1 rewards instead of 0/1, larger batches, ReLU, explicit "suicide warning" flags for 1–2 Provinces left, AdamW. A -0.5 suicide penalty cut suicides but did not improve win rate — [Dominion part 2](https://ianwdavis.com/dominion2.html) (**read**).
- Part 3 (full game, action cards), partial. Buy decisions rank every card by a preference. Secondary decisions are hand-coded: Money Lender always played; Moat always revealed; non-terminal actions first. Cellar compares each hand card to the **expected preference of a card drawn from the deck**, using known deck contents but not order. Trashing treats cards ranked below an END pseudo-card as negative buys. Illegal actions for PPO are handled by subtracting 10 from their logits, not full masking — [Dominion part 3](https://ianwdavis.com/dominion3.html) (**read**, summary; the fetch did not return a feature list for the full-game networks).
- Part 3 results. PPO lost 85–93% of games to the GA on First Game and 70% on Interaction. On Size Distortion, PPO's Witch strategy was described as an even match. Tabular Monte Carlo lost 54% on First Game. No game counts are given for these — [Dominion part 3](https://ianwdavis.com/dominion3.html) (**read**).

### Inferences
- The Dominion lesson that transfers is "mask illegal actions" (already done in this project) and "thermometer-encode small numeric state" (not yet tested here). Dominion's state is too small to say anything about hidden-zone encoding.
- Cellar is the only Dominion mechanism that uses deck composition. It is a hand-coded expectation over the remaining deck and is the closest analogue to a draw-value feature. Under Evan's self-discovery rule it can only be used as a learned feature, not as a hand-written rule.

### Gaps
- No Dominion article gives hand, discard or remaining-deck features for a learned network. Part 3's full-game feature list could not be read in the fetch.
- Part 3 gives no game counts for the full-game comparisons, so its numbers cannot be checked for variance.

## Key Question 2: How do other card-game AIs encode hidden zones, card text and action targets?

### Takeaway
Hidden-hand encodings come from predictive belief models (Gin Rummy, Big 2) or from search over sampled hands. Card-text and attribute encodings generalise to unseen cards, but in a drafting setting only. Action encoding works best as structured tuples scored against the state, not as flat indices.

### Cited Findings
- Hearthstone survey: the unknown opponent hand breaks minimax tree search, so some work learns predictive models of the opponent's hand — [Many AI Challenges of Hearthstone](https://arxiv.org/pdf/1907.06562) (**snippet**).
- Hearthstone deep RL (2023): trains from scratch with deep RL and fictitious play, no look-ahead search. Motivation: hidden deck and hand make planning hard. The paper reports that its models beat a top-10 human streamer in all best-of-5 full-game matches, with no numbers given. State encoding, action encoding, architecture and results are not in the abstract — [arXiv 2303.05197](https://arxiv.org/abs/2303.05197) (**abstract**). The HTML/PDF body was not read.
- Gin Rummy hand estimator: one-hot 52-card input, outputs a 52-length prediction of the opponent's hand — [GinRummyAlgorithm](https://github.com/rxng8/GinRummyAlgorithm) (**snippet**).
- Big 2 self-play under imperfect information: the acting player's hand is a padded list of card ids, encoded with masked self-attention and pooled over valid cards — [arXiv 2605.28863](https://arxiv.org/pdf/2605.28863) (**snippet**).
- Card text and attributes in drafting (MTG, not game play). One-hot card identity gives 67.80% top-1 pick accuracy on seen NEO picks, and cannot represent unseen cards. Attribute features plus Sentence-BERT text embedding give 67.76% on seen cards, and 33.57% on average over unseen sets, against 23.79% for random 1024-d vectors. Best combination (features + meta + image) gives 42.87% on unseen sets. Metric is top-1 match to the human pick, not win rate; the 17Lands "meta" features use human pick statistics — [arXiv 2407.05879](https://arxiv.org/html/2407.05879v1) (**read**).
- Axie Infinity (1v1 card game, 23,149,125 legal actions): each action is a 6×12 matrix (card number plus position). A learned embedding maps actions to a low-dimensional space, and the Q-function scores state and action together (action-conditioned). The agent picks the k feasible actions nearest a raw actor output and takes argmax Q over them — [arXiv 2206.12700](https://ar5iv.labs.arxiv.org/html/2206.12700) (**read**). The paper says the embedding is learned without human priors; it is not clear whether the 6×12 matrix is decomposed into card and target parts (the paper does not say). The paper also contradicts itself: Section II says 6×12, Section IV says the DouZero adaptation uses 2×12.
- Slay the Spire (developer write-up, "Part 3"). Version 1 is a logistic model over counts of 113 cards (114 params). Version 2 maps 25 card features through an MLP into a 32-wide vector, and a 308-feature state into 128. Card ID embeddings were added in one variant. In-game (50 seeds, same agent): mechanical features only ranked 1st; adding card ID embeddings ranked 4th of 4, and the author concludes that embeddings "learned human pick biases" — [DEV Community part 3](https://dev.to/doronsinger/part-3-good-models-finish-last-2n6a) (**read**). Offline accuracy went the other way: 55.8% with embeddings vs 53.5% without. Beat-expert counts were 12 vs 16 (out of 50). This is one author, no CI.
- Slay the Spire, earlier write-up: encoding each card's effects as ~25 numeric fields; normalisation made different cards look identical; mean-pooling hid which hand slot held which card — [DEV Community](https://dev.to/doronsinger/part-2-looking-where-the-light-is-12p5) (**snippet**).
- Slay the Spire 2 agent: distributed PPO, ~234K params, learned card embedding tables, 13-stage curriculum — [cmcour deep dives](https://cmcour.github.io/sts2Showcase/) (**snippet**).
- Pokémon TCG (cabt engine): self-play PPO with a pointer-style policy over a variable list of legal options; board state embedded to a vector; ~0.5M params — [pkm-cabt-ppo model card](https://huggingface.co/TomatoCream/pkm-cabt-ppo) (**snippet**, not peer-reviewed). DeNA CEDEC 2026 talk (Pokémon TPC Pocket): search was impractical under imperfect information, so state evaluation relied on heuristics; an "Action Builder" layer sits between the RL agent and the engine — [invenglobal summary](https://www.invenglobal.com/articles/24133/how-reinforcement-learning-ai-tackles-the-complex-rules-of-pok%C3%A9mon-trading-card-game-pocket) (**snippet**).
- LOCM: five years of competitions; ByteRL is described as the state-of-the-art agent; the 2023 summary covers the approaches and their results, but the abstract does not give numbers — [arXiv 2305.11814](https://arxiv.org/abs/2305.11814) (**abstract**; ByteRL claim **snippet**).

### Inferences
- Hidden zones: no source found encodes the opponent's hand as a learned belief for a TCG pilot in detail. Belief-of-hidden-hand is the common pattern (Gin Rummy, Big 2), so a belief head is a plausible next step, but it is not the bottleneck for situational Trainers.
- Action targets: the Axie factorisation (structured action vectors, scored against the state) is the closest published match to "options scored against encoded state" in this project.
- Identity embeddings: the Slay the Spire result suggests learned identity embeddings can absorb the bias of the training decks. This matters here because the project's identity embeddings were learned from human-coherent decks, and the policy has to rely on card-level function, not deck-specific popularity. This is one author's result, so it is a hypothesis to test, not a finding.

### Gaps
- No LOCM or Hearthstone paper was opened in full, so their state and action encodings are unverified here.
- No source found for hidden-zone encoding of the remaining deck in a TCG (the project's main question) beyond the Dominion Cellar expectation.

## Key Question 3: Which choices measurably helped, with numbers?

### Takeaway
Measured gains exist, but each is from one paper or one author and is either on a toy game or on a different task (drafting or imitation). The best-supported choices are action masking, structured action encoding with a learned action-conditioned scorer, and text or attribute features for generalisation to unseen cards. The Slay the Spire result cuts against card-identity embeddings for play.

### Cited Findings
- Action masking: "biggest breakthrough" in Dominion (qualitative; win rate under 20% before, learned Big Money after) — [Dominion part 2](https://ianwdavis.com/dominion2.html) (**read**).
- Thermometer / count-based numeric encoding: win rate 20% → 30% → 40% on the six-card Dominion game; no variance reported — [Dominion part 2](https://ianwdavis.com/dominion2.html) (**read**).
- Set-level / entity encodings and identity-based attention: not tested in any source read here, so no numbers.
- Learned action embedding + action-conditioned Q: 49.86% vs DouZero 44.77% and DouZero+pooling 42.83% win rate, 174k games per method, one game, no seeds or CI — [arXiv 2206.12700](https://ar5iv.labs.arxiv.org/html/2206.12700) (**read**). The paper says the variance is "small enough to show statistical significance" but names no test. On teams 2 and 6 the method did not beat DouZero. Decision time 7.4 ms vs 18.7 ms (median 5.6 vs 8.7).
- Card text embedding: features + text reach 67.76% seen / 33.57% unseen-average, vs 23.79% random vectors on unseen sets; the best combination (features + meta + image) reaches 42.87% unseen — [arXiv 2407.05879](https://arxiv.org/html/2407.05879v1) (**read**). Note the meta features are derived from human pick data.
- Card-ID embeddings in a human-imitation setting: offline accuracy up (55.8% vs 53.5%), in-game rank down (4th vs 1st of 4) — [DEV Community part 3](https://dev.to/doronsinger/part-3-good-models-finish-last-2n6a) (**read**).
- Adding more data from a weaker player set: made the model confused and was dropped (Slay the Spire, qualitative) — [DEV Community part 3](https://dev.to/doronsinger/part-3-good-models-finish-last-2n6a) (**read**).

### Inferences
- Several reported gains come from imitation or pick accuracy, which does not measure play. Only the Dominion and Axie numbers are play results, and they are on small or single games.
- The project's ground truth is human-level decklists, so the Slay the Spire lesson (offline gains that do not carry to play) should be checked against the deck-level metric, not the pick accuracy.

### Gaps
- No ablation with seeds and CIs for any state-representation choice in a card game was found in the sources read.

## Key Question 4: What do these imply for a policy that never tries a situational card?

### Takeaway
The read sources do not contain a fix for under-selected situational Trainers. The most defensible candidates are (a) scoring options with a one-step lookahead from the existing value head (afterstate value), and (b) an action-conditioned option encoder where the option interacts with the state through attention. A feature such as "damage after PlusPower" is a hand-built shortcut, so under Evan's rule it needs his approval first.

### Cited Findings
- The Axie action-conditioned Q scorer (above) gives a direct route from the option to its value, which is the gap the project has (value head credits the card; policy head does not) — [arXiv 2206.12700](https://ar5iv.labs.arxiv.org/html/2206.12700) (**read**).
- Hand-coded Cellar (Dominion) uses an expected card value over remaining deck contents to value a discard or draw choice — [Dominion part 3](https://ianwdavis.com/dominion3.html) (**read**). Hand-coded rules like this are a shortcut the project would have to learn instead.
- The DeNA talk reports that tree search was impractical under imperfect information, and state evaluation was hand-built — [invenglobal summary](https://www.invenglobal.com/articles/24133/how-reinforcement-learning-ai-tackles-the-complex-rules-of-pok%C3%A9mon-trading-card-game-pocket) (**snippet**).

### Inferences
- The gap is structural: the policy head scores options against a state encoding that does not contain the option's effect. The value head evaluates the state, not the option. So the policy never sees "what would this card do now" unless the option encoder can compute it.
- Candidate experiments, in order of cost, all self-discovered (no human data, no hand-written rules):
  1. **Afterstate scoring.** For each legal option, run the engine to the afterstate and read the existing value head there; add that score to the policy logit (or distil into it). This uses only the agent's own critic. Cost: one engine step per option, up to 128 per decision.
  2. **Action-conditioned option encoder.** Encode each option as a tuple (card token, target token, action type) and let it cross-attend to the state tokens, so the option embedding can represent interactions such as HP vs. damage. This follows the Axie factorisation. Cost: small (one attention layer over options).
  3. **Remaining-deck count vector as input.** The player knows its own decklist and what has been seen, so the composition of the remaining deck is part of the information state (not a hidden-order leak). Dominion Cellar shows deck-composition expectations are useful for draw valuation. Cost: small.
  4. **Thermometer encoding** of HP, prize count and deck size, as in Dominion part 2. Expected gain: small, and the Dominion gain was on a toy game.
- Hand-built "damage after PlusPower / knockout threshold" features are the closest match to what Evan asked about, but they are hand-built shortcuts. They need his explicit approval under the self-discovery rule. The afterstate scoring in candidate 1 gets the same information from the engine without writing rules.

### Gaps
- No source read tests situational-card valuation directly. All implications are inferences from general mechanisms.
- The afterstate approach depends on the engine being able to clone or step a state cheaply. This was not checked against the project's engine.

## Source list (all cited above)
Read in full (via WebFetch): dominion.html, dominion2.html, dominion3.html, arXiv 2206.12700 (ar5iv), arXiv 2407.05879, DEV part 3 (Slay the Spire). Abstract only: arXiv 2303.05197, arXiv 2305.11814. Snippet only: 1907.06562, 2605.28863, GinRummyAlgorithm, DEV part 2, cmcour, pkm-cabt-ppo, invenglobal. Not used: pojo.com and Bulbapedia (not requested; no 403 retries made).

Caveat: the Part 3 Dominion summary and the Slay the Spire post were summarised by WebFetch's model. Exact quotes should be checked against the page before they are used in a paper.
