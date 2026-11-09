# How RL agents learn the choices inside multi-step card actions (discard / search / target prompts)

Scope note: ~12 tool calls. Several primary PDFs (AlphaStar, OpenAI Five, SAC-Discrete, TStarBot-X) came back as unreadable binaries, so claims about them rest on secondary summaries or are marked "from memory, unverified". Nothing here is card-specific shaping unless stated.

Local facts folded in (from the coordinator, notes/audits.md): C68/X1 random answers to the pilot's own Trainer prompts change nothing (+0.002 ± 0.009, 6,080 games/variant). C71/X10 permuting Trainer identities costs 70 Elo. A2: C70/X5 swapping a list's 6 Trainers for basic Energy scores 0.444±0.015 vs its copy, off-type Energy 0.484, Clefairy Doll (near-blank) 0.506; Doll minus basic Energy +0.062±0.010, so the lists' Trainers only tie a near-blank card. C69/X3 the Trainer deficit is the same off-mirror as in the mirror (-0.040 vs -0.039), so it is general. Reading: the pilot's Trainer play is no better than random or blank, while it does condition on which Trainer it holds. In ar/train.py the entropy term is `ENT * mean over all steps of the full-masked-softmax entropy` (lines 96-103), i.e. a flat, un-normalised bonus where a 40-option prompt can carry up to ~3.7 nats and a 2-option prompt at most 0.69.

---

## 1. Action factorisation: how published agents condition a sub-choice on the triggering card, and does it matter?

### Takeaway
The strong large-scale agents factor an action into ordered heads (type, then unit/target via a pointer over entities) and condition later heads on earlier ones; the only direct ablation I could read says autoregressive factoring is best overall but branching/independent heads are cheaper and often close. Nobody I found reports a card-game ablation of "target conditioned on the card that triggered it". Your pilot already has the structurally right thing (each prompt is its own step, pointer over tokens), so the open question is whether the prompt "knows" which card triggered it, not whether to factor.

### Cited Findings
- AlphaStar generates each action component sequentially, each conditioned on all previous ones (action type, delay, queue, selected units, target), with a pointer network over the available entities for unit choices because the entity count varies — [aiwiki AlphaStar summary](https://www.aiwiki.ai/wiki/alphastar) (secondary source; DeepMind blog/paper not read directly, [InfoQ](https://www.infoq.com/fr/news/2019/04/deep-mind-ai-defeats-top-players/) repeats "auto-regressive policy head with a pointer network").
- TStarBot-X reimplements this (sequential prediction for the selection head, pointer network for the target) but reports that an earlier multi-binary selection head "generally works well and is much more efficient" than sequential prediction — [TStarBot-X](https://arxiv.org/pdf/2011.13729) (via search snippet; PDF unreadable, so no numbers).
- A 2026 cross-sectional study (6 factorisations x PPO/SAC/DQN x 3 action-space types x 4 envs, 220 configs) finds auto-regressive actions give the highest overall performance, branching dueling architectures the best compute/performance balance, and proposes VDN-PPO / PPO-MIX (branching critic assigning credit across heads) beating other PPO factorisations — [Flavin & Sen 2026, arXiv 2606.26574](https://arxiv.org/abs/2606.26574) (abstract only; toy/continuous-control envs, not card games).
- A paper on compound-action PPO argues the joint probability makes clipping zero out gradients, and computes the loss per sub-action instead — [Joint action loss for PPO](https://astro.paperswithcode.com/paper/joint-action-loss-for-proximal-policy) (seen only as a search-result summary; fetch failed; verify before relying).
- Clash Royale agent SEAT splits play into a selection part (which card) and an attention part (how the card is used/where), trained from scratch with deep RL — [IJCAI 2019 SEAT](https://ijcai.org/proceedings/2019/631) (search summary only; I did not read the ablations).
- Dou Di Zhu: a two-stage hierarchy (a decomposition network proposes a decomposition, a move-proposal network picks the concrete card group) handles the combinatorial space — [Combinational Q-learning for Dou Di Zhu](https://arxiv.org/pdf/1901.08925.pdf).
- Invalid-action masking: masking zeroes the logit gradient of illegal options (their 4-action example: unmasked gradient [0.75,-0.25,-0.25,-0.25] vs masked [0.67,-0.33,0,-0.33]); benefit grows with the size of the invalid space; training with masking then removing it degrades — [Huang & Ontanon, arXiv 2006.14171](https://arxiv.org/abs/2006.14171) (read via ar5iv summary). They do not analyse entropy under masking.
- An MTG benchmark (MTG-Causal-RL, 2026) uses one flat 478-slot masked discrete action space with a dedicated 122-slot TARGET block; typically only 2-15 actions are legal — [arXiv 2605.06066](https://arxiv.org/pdf/2605.06066). This is a flat-slot design (a target slot has no explicit link to the triggering spell); abstract/first part only.
- Gaps in what exists: Pokemon TCG RL I found is a thesis, a Hugging Face PPO self-play checkpoint (potential-shaped on prize differential, evaluated only vs random) and TCGJax (JAX engine, 153K steps/s with PPO); none documents sub-prompt handling — [thesis](https://digitalcommons.ncf.edu/theses_etds/7022), [HF pkm-cabt-ppo](https://huggingface.co/TomatoCream/pkm-cabt-ppo), [catalyzex TCGJax listing](https://catalyzex.com/author/Chi%20Jin).
- Hearthstone: Cardsformer pairs a prediction model (forecasts state changes from card text, trained on offline trajectories) with a policy model, improving data efficiency and generalisation to untrained cards — [IOS Press FAIA230581](https://ebooks.iospress.nl/doi/10.3233/FAIA230581) (abstract level).

### Inferences
- Because your prompts are separate PPO steps with a pointer head, you already have the "autoregressive" form in the sense that the later prompt sees the state after the earlier choice. What may be missing is an explicit marker of which card/effect opened the prompt. If the token set does not flag "the card being resolved" (e.g. a pending-effect token or a flag on the source card token), the pointer head must infer the prompt's meaning from board state alone, which is hard for rare prompts. I have not verified what rl/token_model.py provides; check first.
- Factoring is unlikely to be the lever: X1 says the learned choices are no better than random, which is a learning-signal problem (sections 2-4), not an expressiveness problem.
- Loop change: (a) 2-minute code check: does the token input include a "source of this prompt" feature (card id/text of the effect being resolved, prompt type)? If not, add one learned flag/embedding on the triggering card token and the prompt-type token; this is game-agnostic (the engine's own prompt metadata) and allowed. Cost: small ar/train.py/model edit plus a 70-minute screen; X1 re-run afterwards (~6,000 games) is the decisive readout. (b) Do not switch to a flat slot design or a full autoregressive rebuild; the evidence for it is from toy/control tasks.

### Gaps
- No readable primary text for AlphaStar/OpenAI Five/TStarBot-X heads; no card-game paper with an ablation of "condition target on triggering card"; no Legends of Runeterra, Yu-Gi-Oh, Gwent, Forge/17lands agent papers found with sub-prompt details (17lands work I found, [arXiv 2407.05879](https://arxiv.org/html/2407.05879v1), is draft-pick modelling with Siamese card/deck embeddings, not in-game choices). DouZero, Suphx, DeepNash were not searched in depth; from memory (unverified) they use flat or combinatorial move encodings with no sub-prompts, so they are not informative here.

---

## 2. Credit and exploration for many-option sub-prompts: entropy, per-head coefficients, advantage sharing, macro-actions

### Takeaway
A flat entropy bonus summed/averaged over steps gives a large prompt a larger maximum bonus and a larger gradient pull toward uniform than a small prompt; the standard remedies (normalise by log of legal count, per-head coefficients, or a target-entropy controller) are documented in the literature, but I found no published card-game study of them. Your ENT 0 (+0.008, one seed) and ENT -0.005 (-0.018) results are consistent with entropy being a weak lever, not with it being the cause.

### Cited Findings
- PPO loss libraries expose a single entropy coefficient (default 0.01), usable per action head; no normalisation by legal-action count is documented — [TorchRL PPOLoss](https://docs.pytorch.org/rl/main/reference/generated/torchrl.objectives.PPOLoss.html). I found no source that documents normalising the PPO bonus by log(legal options) (search for this returned nothing specific).
- Huang & Ontanon use eta = 0.01 with masked PPO and report nothing on entropy under masking — [arXiv 2006.14171](https://arxiv.org/abs/2006.14171).
- Entropy bonuses over very large action spaces are unstable; a 2025 LLM-RL paper clamps the bonus and auto-adjusts the coefficient — [arXiv 2509.03493](https://arxiv.org/pdf/2509.03493v3) (snippet only; LLM setting).
- Factored critics: splitting the joint value into a shared state value plus one centred advantage stream per head gives per-head credit — [arXiv 2606.26574](https://arxiv.org/abs/2606.26574). Per-sub-action loss avoids joint-ratio clipping zeroing gradients — [Joint action loss for PPO](https://astro.paperswithcode.com/paper/joint-action-loss-for-proximal-policy) (unverified summary).
- From memory, unverified (primary PDF unreadable): SAC-Discrete (Christodoulou 2019, arXiv 1910.07207) sets target entropy to a fraction (0.98) of log|A|, i.e. scales the entropy target by the log of the action count. This is the cleanest published precedent for "normalise entropy by log |options|".

### Inferences
- In ar/train.py the entropy term is the plain mean over steps, so a Trainer prompt with 30-40 options is pushed ~5x harder (in nats) toward uniform than a 2-option prompt, per unit of ENT. With X1 showing the choices are already near-random, this could be hiding or cementing a flat prompt policy, but the ENT 0 result (+0.008) bounds the effect at roughly the noise level unless the effect is confined to sub-prompts.
- Advantage sharing: your trajectory gives each sub-step the same GAE machinery; the credit for "which card to discard" arrives through the value difference at the next state, a delayed and noisy signal over a very long game. A macro-action view (return of the whole Trainer play credited to all its sub-steps) is a variance-reduction trick, but it does not create a signal where the outcome is insensitive to the choice, which may be the real situation (X1).
- Loop change: (a) ar/train.py edit, ~3 lines: replace `ENT * entropy` by `ENT * entropy / log(n_legal)` (normalised entropy in [0,1]) with ENT retuned (try 0.01 and 0.003); allowed (uses only the legal-option count). Cost: one 5-minute ar/ run per seed, three seeds to clear the bar. (b) Variant: ENT applied only on main-phase prompts and 0 on in-Trainer prompts (needs the prompt-type flag, which the engine supplies); ties to experiment 1's flag. (c) Do not expect much: ENT 0 gave +0.008, so a normalised variant is a cheap "last entropy check", not a main hypothesis.

### Gaps
- No published evidence on normalised entropy in masked card-game PPO; no card-game result on macro-action credit sharing; per-head advantage evidence is only from synthetic control tasks.

---

## 3. Should sub-decisions be inside the search / expert-iteration targets?

### Takeaway
Gumbel MuZero's main advantage is a guaranteed policy improvement at the root with very few simulations by sampling candidate actions without replacement, which suits a root with many options (a 30-card search prompt) better than your top-4 probe. The Student of Games handling of chance/selection nodes could not be confirmed from my sources. Direct evidence for "searching sub-prompts" in card games is absent.

### Cited Findings
- Gumbel AlphaZero/MuZero sample actions without replacement at the root and use a policy-improvement rule at root and non-root nodes; they stay effective at small simulation budgets and fix AlphaZero's failure to improve when not all root actions are visited — [Danihelka et al., ICLR 2022](https://iclr.cc/virtual/2022/poster/6418), [paper text](https://mlanthology.org/iclr/2022/danihelka2022iclr-policy).
- Multi-agent Gumbel MuZero extends this to combinatorial action spaces, arguing sampling with replacement wastes visits on high-probability actions — [AAAI-24](https://ojs.aaai.org/index.php/AAAI/article/view/29121/30120) (summary level).
- Student of Games (Schmid et al., Science Advances 2023) combines guided search, self-play learning and game-theoretic reasoning and is proven sound; poker and Scotland Yard results — [arXiv 2112.03178](https://arxiv.org/pdf/2112.03178). My fetch did not reach how it treats chance or selection prompts; ReBeL, DeepNash chance/selection handling not verified.
- Existing local notes (search_and_credit.md Q2) already cover distillation failure modes with weak values; not repeated here.

### Inferences
- A prompt inside a Trainer (e.g. "choose a card to discard") is a one-step decision with a clear counterfactual: roll out each of K candidates (or sampled K by Gumbel top-K) from the same state and compare outcomes. Your current search probes the top-4 moves only at main-phase decisions; prompts inside Trainers have the same structure but are skipped, so they get no distillation signal, only noisy PPO signal.
- Cost concern: a prompt with many options and a delayed, weak outcome effect needs many rollouts to separate candidates; if the true effect of a good discard is small (X1: +0.002 ± 0.009 for random vs policy), the search targets will be mostly noise too, though noise-in-target is at worst neutral, unlike a missing signal.
- Loop change: (a) Short probe (diagnostic, no training): at sampled in-Trainer prompts, run the existing search probe with K=4 sampled by Gumbel-top-k from the policy and measure the spread of candidate outcome estimates versus main-phase prompts. If the spread is near zero, the choices do not matter much and the plateau is not about sub-prompts. Cost: reuse the probe code, maybe 30 minutes of games; allowed (policy plus engine result only). (b) If spread is non-trivial: extend the SEARCH_DISTILL targets to in-Trainer prompts, ≤70-minute screen with the existing distillation loss. (c) Swap top-4 for Gumbel top-k with a sequential-halving budget only if (a) shows signal; this is a bigger change.

### Gaps
- No source on how search agents treat sub-prompts of a played card; the Student of Games chance-node details unconfirmed.

---

## 4. Do agents learn "how to use" a card only after "when to play" it? Curricula and auxiliary losses

### Takeaway
I found no direct evidence for that ordering. What exists: auxiliary prediction losses help in toy RL settings, and Cardsformer predicts a card's effect on state from its text before using it in a policy. Your own data show the pilot learned "which Trainer I hold" (70 Elo) but not "what to do inside it" (X1), and that its Trainers rank no better than a near-blank card (X5), which is consistent with a sequential-learning story but also with the signal being absent.

### Cited Findings
- Cardsformer: a Prediction Model trained on offline trajectories to forecast state changes from card descriptions, feeding a Policy Model; gains in data efficiency and with unseen cards in Hearthstone — [IOS Press FAIA230581](https://ebooks.iospress.nl/doi/10.3233/FAIA230581) (abstract-level; the follow-up AAMAS 2025 abstract uses a T5 encoder, [PDF](https://aamas.csc.liv.ac.uk/Proceedings/aamas2025/pdfs/p2795.pdf)).
- Auxiliary reward/next-state prediction losses improved learning in ARCLE tasks; a label-free prediction head cut seed variance in another 2026 setting — [ARCLE](https://arxiv.org/pdf/2407.20806), [arXiv 2607.11953](https://arxiv.org/pdf/2607.11953) (search summaries; not card games).
- Auxiliary prediction of language sub-goals shapes representations for low-level control — [arXiv 2309.11564](https://arxiv.org/pdf/2309.11564).
- Heuristic from the local data: Doll minus basic Energy is +0.062 ± 0.010 (A2 C70/X5), meaning the pilot rates a near-blank card above Energy but near the lists' Trainers: it does not extract Trainer value.

### Inferences
- A self-supervised head fits the rules (game's own outcomes, no human lists): predict, from the state before a Trainer is played, the change in some engine-visible quantity after it resolves (e.g. next-state features such as hand size, prize difference, board energy count) conditioned on the card and the chosen sub-choices. This forces the encoder to represent what each sub-choice does, independent of win/loss noise. It is card-agnostic (uses state deltas) and transferable to MTG.
- Loop change: ar/train.py edit, ~20-30 lines: an auxiliary regression head on the policy trunk, loss on the observed state delta after each prompt step (weight ~0.1), cost one ≤70-minute screen plus an X1 re-run (6,080 games) as the diagnostic; allowed under self-discovery rules as long as the target is a game-state delta and not a card-kind label. Evidence strength is weak (no card-game precedent in my search), so rank it below sections 1 and 3.

### Gaps
- No paper found showing the "when before how" ordering, no curriculum on sub-choices in card games.

---

## 5. Diagnostics: how others measure whether sub-decisions are learned

### Takeaway
Direct precedents for X1-style "random replacement" probes in card games were not found. The closest documented practices are removing masking at test time (Huang), counterfactual ablations of inputs, and probing representation. X1 and X5 are stronger than anything I found, so the loop's own diagnostics are the main tool.

### Cited Findings
- Huang & Ontanon evaluate by deploying the trained policy without its mask and counting invalid selections (150-165 per episode on larger maps), a "does the policy know what is legal" probe — [arXiv 2006.14171](https://arxiv.org/abs/2006.14171).
- Draft-pick models are scored by top-1 agreement with human picks (55-62% on held-out sets with pre-training), a held-out accuracy measure, not applicable to self-discovery training — [arXiv 2407.05879](https://arxiv.org/html/2407.05879v1).
- The Pokemon TCG HF agent and others report win rate against random only — [HF](https://huggingface.co/TomatoCream/pkm-cabt-ppo), which is not a sub-decision diagnostic.

### Inferences
- Add cheap sub-decision diagnostics to ar/ logging: (1) mean normalised entropy per prompt type (in-Trainer vs main phase); (2) fraction of in-Trainer prompts where the policy's top option has probability above uniform by a margin; (3) the ratio of policy-choice to random-choice outcome (X1) per Trainer type, reported with CI. A low normalised entropy with X1 still null means the choice is deterministic but wrong or irrelevant; a high one means unlearned.
- Loop change: log item (1) and (2) from existing rollouts, ~10 lines, zero extra game cost; allowed. Run before spending screens on experiments 2-4 because it tells which of "unlearned" vs "irrelevant" applies, and A2's X5 (+0.062 ± 0.010 for a near-blank card over basic Energy) suggests the main issue may be the value of the Trainer itself rather than its prompts.

### Gaps
- No published random-replacement or counterfactual sub-choice probe in a card-game RL paper located.

---

## Priority order (cost-weighted)
1. Free diagnostics: normalised entropy per prompt type and top-option margin (Q5).
2. Code check for a source-of-prompt feature; add if absent (Q1).
3. Search-spread probe at in-Trainer prompts (Q3), then distill if non-trivial.
4. Normalised-entropy ar/ edit (Q2), 3 seeds.
5. Auxiliary state-delta head (Q4), weakest evidence.
Caveat for the report writer: A2 shows Trainers only tie a blank card even off-mirror, so fixing sub-prompts alone may not lift Trainer value; the plateau could be in the Trainer's valuation (credit for playing it at all) as much as in its inner choices.
