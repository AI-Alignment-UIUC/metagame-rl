# Pokémon TCG RL: deck design + play, ground truth, and engine comparison

Research notes, written 2026-09-07. Covers the state of crystalskies' `Pokemon_TCG_RL` simulator (v4), a comparison against ryuu-play, the representation fixes, the dual "design a deck + play it" self-play problem, how to get ground truth from historical Worlds metas, and the most promising solutions. Every number below was measured in this session unless marked as an estimate; scripts are in `notes/scripts/`.

---

## 0. Context

- Project goal (Evan, 2026-02): an RL system that (1) represents a TCG's state and action space, (2) learns to play a deck via self-play, (3) abstracts that knowledge to build/draft decks. Started on MTG (MageZero / XMage fork), switched to Pokémon TCG because there is no stack or priority passing, so the action space is simpler.
- crystalskies built `Pokemon_TCG_RL` (https://github.com/SuryaSGit/Pokemon_TCG_RL): NumPy-only PPO/DQN agents on a hand-written Python engine. v3 = 30-card half decks; v4 = full 60-card Mega Starmie ex vs Mega Lucario ex, 41 distinct cards. Local clone: `Mon/Pokemon_TCG_RL`.
- crystalskies' reported blocker: deck-search cards (Ultra Ball, Night Stretcher) "increase the action space by too much", and 60-card decks were "pretty hard to get good results" even with LLM help.

---

## 1. Problem statement

Two coupled games:

- **Inner game (play).** Two fixed 60-card decks; imperfect information (hidden hands, shuffled decks, prizes); long horizons; sub-choices inside card effects (search, discard, targets); first-player restrictions; special conditions.
- **Outer game (deck design).** Choose a decklist. The payoff matrix of the outer game is the matchup table produced by the inner game under whatever play policy exists. Card metas are non-transitive (rock-paper-scissors on top of a raw power axis, the "spinning top" structure), so **the target is an equilibrium mixture / population of decks, not a single optimal deck**.

The research question: can an agent, given only the card pool and the rules, (a) learn to play any deck, (b) learn to build decks against a meta, and (c) rediscover the historical Worlds metagame from scratch, which then serves as ground truth?

---

## 2. State of the current simulator (Pokemon_TCG_RL v4)

Files: `v4/ptcg_env.py` (3,046 lines; ~1,260 in `GameEngine`), `v4/rl_agents.py`, `v4/train.py`.

### 2.1 Representation as built

**Observation, 234 floats** (`StateEncoder`):
- 12 board slots (my/opp active + 5 bench each) x 13 features: hp fraction, energy by 4 types, total energy, Pokémon identity as ONE SCALAR (id/16), stage, is_ex, is_mega, has_tool, retreat cost, ability ready.
- Hand: a 6-bucket histogram by card type + per-slot energy type for 12 hand positions. **Non-energy hand cards have no identity in the vector.**
- Scalars: opp hand size, deck sizes, KO counts, energy/supporter used, turn, going first, stadium, black belt.
- Pending choice: 1 flag + 12 option slots x 4 features (valid, category, hp frac, id scalar). Ultra Ball discard options show card TYPE only.
- Not encoded: discard pile, remaining deck by name, status conditions, attack restrictions, tool identity.

**Action space, 295 flat** (`ActionMapper`): every card action is indexed by HAND POSITION (cap `MAX_HAND = 12`) x up to 6 target slots. Search/discard effects set `pending_choice` and expose 12 `CHOOSE` actions over the first 12 matching deck/hand positions (`opts[:12]`). 19 pending-choice types. Sequentialising Ultra Ball into discard1 -> discard2 -> pick is the RIGHT design (same as ryuu-play's prompt queue); the problems are the encoding around it.

### 2.2 Measured problems (200 games each, random and built-in heuristic policies)

| Metric | Random | Heuristic |
|---|---|---|
| Decisions with >=2 legal same-verb actions on different card names (policy cannot tell them apart) | 31.9% | 37.0% |
| Ultra Ball picks that could not reach every Pokémon in deck (truncated to 12 positions) | 267 / 1125 | 245 / 463 |
| Petrel picks truncated | 94 / 132 | 32 / 34 |
| Fighting Gong picks truncated | 221 / 579 | 138 / 194 |
| Choice option slots occupied by duplicate copies | 30% | 36% |
| Largest hand seen (cards past index 12 are unplayable) | 15 | 37 |
| Decisions with hand > 12 | 16 | 367 (2.6%) |
| Games ending by deck-out | 138 / 200 | 18 / 200 |
| Time per decision (step + legal mask + encode) | 78 us | 74 us |

Interpretation: in about a third of decisions the agent must choose between e.g. Ultra Ball and Switch, or Riolu and Meowth ex, while the observation only says "you hold two items". That, not 60-card complexity, is the likely reason training stalled. Truncation makes which Pokémon Ultra Ball can find depend on shuffle order. The hand cap feeds back: cards past index 12 cannot be played, so hands snowball.

Speed is NOT a bottleneck: ~13,000 decisions/s single-threaded pure Python, ~180 heuristic games/s.

### 2.3 How cards are implemented

Entirely hand-coded Python. Cards are literals in `build_starmie_deck()` / `build_lucario_deck()` with a string effect tag; the engine dispatches on tags with if/elif chains: 79 branches over 48 distinct tags spread across the legality mask, item/supporter handlers, choice resolver, attack handler, ability handler, and the state encoder's option features. One new card touches 4-5 functions (~30 lines/card including duplicated bookkeeping). Does not scale past a few dozen cards.

Card vocabulary: Starmie deck 26 distinct names, Lucario 22, union 41, 17 distinct Pokémon names.

---

## 3. Engine comparison: ryuu-play vs Pokemon_TCG_RL v4

ryuu-play: https://github.com/keeshii/ryuu-play (MIT, TypeScript, 111 stars, created 2021, last push 2026-06-18, actively maintained with spec tests).

| Dimension | ryuu-play | Pokemon_TCG_RL v4 (crystalskies) |
|---|---|---|
| Language / runtime | TypeScript monorepo (`@ptcg/common`, `sets`, `server`, `play` Angular client, `cordova`, `simple-bot`), Node 18+. Node 24.14.1 is installed locally. | Pure Python + NumPy, single-file engine |
| Card pool | ~890 card files: Base/Jungle/Fossil/Team Rocket (263), Ruby & Sapphire/Sandstorm/FRLG (325), HGSS/DP/BW/XY-era (274; folders mislabeled "black-and-white-2..4" contain XY cards: Lysandre, VS Seeker, Seismitoad-EX, Shaymin-EX, Battle Compressor, Lucario-EX), 11 Sword & Shield cards, 31 shared. **Pool spans ~2010-2015.** | 41 cards (2025-26 Standard: MEG, POR, ASC, TWM, SSP...) |
| Modern mechanics | CardTag: SP, EX, GX, LV_X, ACE_SPEC, FOSSIL. No V/VSTAR/VMAX/Mega ex/Tera. Stage includes RESTORED. 11 energy types, 5 special conditions. | ex (2 KO points), Mega ex (3 points, turn ends), tools, stadiums, 3 status effects, no prizes (KO points instead), 6 energy types |
| Card definition | One class per card; `reduceEffect(store, state, effect)`; multi-step effects as generator functions yielding typed prompts. Ultra Ball = ~90 lines with legality, both discards, search, reveal, shuffle in ONE place. | Effect-tag strings + if/elif branches in 4-5 functions per card |
| Sub-choices | 27 prompt types: choose-cards (with filter, min/max, allowCancel, blocked), choose-pokemon, attach-energy, choose-energy, choose-attack, choose-prize, coin-flip, confirm, move-damage, move-energy, order-cards, put-damage, select, show-cards, shuffle, alert, invite-player. The prompt carries the explicit candidate list. | `pending_choice` dict with positional option list truncated to 12 |
| State model | `State{cardNames, logs, rules, prompts, phase, turn, activePlayer, winner, players}`; `Player{deck, hand, discard, stadium, supporter, active, bench, prizes[], retreatedTurn, energyPlayedTurn, stadiumPlayedTurn, stadiumUsedTurn, marker}`; `PokemonSlot{damage, specialConditions, poisonDamage, burnDamage, marker, pokemonPlayedTurn, pokemons, energies, trainers}`; `CardList` | `GameState{players, current_player, turn_number, active_stadium, ...}`; `PlayerState{deck, hand, active, bench, discard, ko_count, flags, pending_choice}`; runtime fields on `PokemonCard` |
| Actions | `PlayCardAction(player, handIndex, target)`, `ResolvePromptAction`, game-actions (attack, retreat, pass turn, ability), reorder/abort/etc. | 295 flat integer actions |
| Legality | None enumerated. Illegal action throws `GameError`; store restores a deep-cloned backup. Bundled `SimpleBot` finds moves by constructing candidates and trying them in a `Simulator` (which deep-clones state and auto-resolves prompts via a `BotArbiter`), scoring with `state-score`. | `compute_legal_mask()` returns a 295-mask directly |
| Rules config | `Rules{formatName, firstTurnDrawCard, firstTurnUseSupporter, noPrizeForFossil}`; KO of POKEMON_EX gives +1 prize | Hard-coded: first player cannot attack turn 1, no evolving the turn played |
| Throughput | **Unmeasured.** Every `dispatch` deep-clones the state for rollback; Simulator clones again. Estimate: 1-2 orders of magnitude slower per decision than v4. | 13k decisions/s, ~180 games/s (measured) |
| RL fit | Right architecture (effect DSL + prompt queue + explicit candidate sets = what pointer-style policy heads want). Needs: legal-move enumerator, observation exporter, Node<->Python bridge or in-Node inference, modern card tags, and every modern card written. | Runs today, fast, Python. Needs: representation rewrite (Section 4) and eventually an effect DSL. |
| Human play surface | Public server https://ptcg.ryuu.eu/, Matrix chat, documented bot registration on a private server, replay interface in `common/game/replay.ts`. | Flask GUI, local only |
| Per-year formats | Each card class carries `set` / `fullName` set code (e.g. `'Ultra Ball PLB'`), so per-year legal pools can be reconstructed. | n/a |

**Alternatives checked and rejected:** TCG ONE (open Groovy card files up to gen8 in `tcgone-engine-contrib`, but the engine is closed-source and cannot be run locally); DeckGym-core (Rust, fast, but simulates TCG *Pocket*, a different game); NeonSky/open-pokemon-tcg (C++, dead since 2020); eduardo089/pokemon_tcg_engine (empty).

**Verdict:** ryuu-play is the right *architecture* and the best open engine for the physical game, but not the engine out of the box: wrong era, no enumerator, unmeasured/likely slow stepping, TypeScript. For the two-deck experiment keep v4 and fix its representation. For a larger pool, either fork ryuu-play and build the RL harness in Node, or port ryuu-play's design (store + typed prompts + one effect function per card) into Python using its ~890 cards as reference implementations. If the target is the 2010-2015 pool (for historical ground truth, Section 5), forking ryuu-play directly becomes attractive because the cards already exist.

---

## 4. Representation plan

### 4.1 Step 1: index by card identity (drop-in for v4)

- **State:** hand, discard, remaining deck (decklist minus seen; legitimately known), and opponent discard as COUNT VECTORS over the 41-name vocabulary; board slots keep per-slot features but identity becomes a 17-way one-hot; pending choice = 19-way type one-hot + remaining picks + 41-way candidates-by-name (needed for Pokégear, whose options are information).
- **Actions:** "play card X" is one action per name (copies are interchangeable); search choice = softmax over matching names (max 11 here), no truncation, no duplicates; Ultra Ball discards = two picks by name. Hand cap disappears.

| Block | Lean | Full |
|---|---|---|
| Board, 12 slots (17 id one-hot, hp, 6 energy, total, tool, retreat, ability; Full adds 3 status, cant-attack, 2 blocked-attack, shadow bound, played this turn, ignition, legacy) | 336 | 456 |
| Count vectors, 4 x 41 | 164 | 164 |
| Scalars | 15 | 15 |
| Pending choice (19 + 1 + 41) | 61 | 61 |
| **Total** | **576** | **696** |

Flat identity-indexed action space: ~106 (Starmie) / ~83 (Lucario) vs 295 now, with strictly more information. Use the union vocabulary for both seats so weights are shared.

### 4.2 Step 2: tokens + transformer + pointer heads (scales to any pool)

- Every visible card instance is a token: card embedding + zone/owner embedding + runtime numbers. Token types: global (1), board slot (<=12), my hand card, discard cards (or count-weighted embedding bag), my remaining deck (embedding bag), prompt candidates (one per legal option while a prompt is open). ~100-200 tokens/state; 2-4 encoder layers at width 128-256.
- Policy = small verb head (play/attach/evolve/attack/retreat/ability/end/resolve) + pointer head scoring candidate tokens by dot product with a query from the pooled state. Search prompts become a softmax over eligible deck tokens with no cap. Multi-step effects stay sequential (AlphaStar-style autoregressive decomposition).
- Card embedding: learned id table (no generalisation) vs structured features + rules-text embedding via a frozen sentence encoder (new cards get a representation immediately) with a learned id residual. The second is what makes drafting/deckbuilding transfer possible.
- Reference: MageZero (MTG) already tokenises everything: 2M-slot hashed sparse feature space, ~200 active features/state, `nn.Embedding(sparse=True)` 2M x 512, one `TransformerEncoderLayer` d=512, mean-pooled; four policy heads (player priority 128 deck-local, opponent priority 128, targets 128 matchup-local, binary 2); AlphaZero-style MCTS (PUCT, c=1.0), ~250 games/hour on 13 threads at 300 sims. Its weak point is the flat deck-local action heads, which pointer heads replace.

The wall for a full-format agent is the ENGINE (every card's logic must exist), not the representation.

---

## 5. Ground truth: how to know it plays at human level

Only one real ground truth exists: humans playing against it. Everything else is a proxy. Ranked:

1. **Live human play.** ryuu-play hosts a public server and documents bot registration. TCG ONE's *Legacy* format is exactly the HGSS-BW era (plus dozens of retro formats and a ranked ladder at play.tcgone.net), so players who know the 2010-2015 pool exist and can be recruited. Design: fixed decklists from archived Worlds top cuts buildable in the pool; mirrors and cross-matchups with seats swapped (deck choice must not confound play skill); ~200 games per opponent pool (win-rate SE ~5 pts at 100 games, ~3.5 at 200). The defensible claim is "beats Legacy-ladder players on fixed lists within this pool".
2. **Historical tournament data** (ground truth for the META, not for a single game). Limitless and pokemon.com archive Worlds decklists 2012-2015 with placements. Checks: archetype rediscovery (max card-overlap similarity of each historical list to the agent's population, and the reverse), whether winning archetypes sit in the equilibrium support, matchup directions vs era write-ups. Human metas are never at equilibrium; expect qualitative agreement.
3. **Expert decision matching.** 2013 and 2014 TCG Masters finals are archived on YouTube; more top-cut streams exist. Transcribing gives a few hundred expert decisions. Small but real.
4. **Proxies:** puzzle positions with provable answers (lethal, deck-out avoidance, N-count math); ryuu-play's SimpleBot as floor; big-budget MCTS as a relative scale.

**Pool coverage measured (ryuu-play):**
- James Good, Worlds 2013 3rd, Blastoise/Keldeo: 57/60 implemented; missing Black Kyurem-EX x2, Cilan x1.
- Daniel Altavilla, Worlds 2014 9th, Blastoise/Keldeo: 57/60; missing Black Kyurem-EX x2, Black Kyurem x1. (Professor's Letter IS implemented; a name-normalisation false negative.)
- 70 of 88 era staples present. Buildable archetypes: Darkrai/Hydreigon, Blastoise/Keldeo, Eelektrik/Zekrom/Rayquaza-EX, Landorus/Mewtwo, Yveltal/Garbodor, Seismitoad/Garbodor, Lucario/Hawlucha. **Team Plasma is missing** (Deoxys-EX, Thundurus-EX, Genesect-EX, Plasma Energy, Colress Machine), as are Black Kyurem-EX, Lugia-EX, Registeel-EX, Magnezone, Yanmega, Reuniclus, Ninetales, Victini, Suicune, Absol, Celebi/Kingdra/Typhlosion Prime.
- **Per-year legality is required**: the pool mixes sets that never coexisted (Junk Arm 2010 + VS Seeker 2014). Build "Worlds 2013" / "Worlds 2014" pools from set codes; otherwise the agent invents decks that never existed.

**Modern-format contrast:** Pokémon TCG Live exports battle logs; parsers/replay viewers exist (kagd/pokemon-tcg-battle-replay, ptcglreplay.com, Trainer Hill battle journal), so a large human-game corpus for chess-style move-matching is collectable for the modern pool. Nothing comparable exists for 2010-2015 (PTCGO is gone). This is the strongest argument for the modern-card path if corpus evaluation matters.

---

## 6. Deck-design RL: the plan

Formulation: outer game solved by a PSRO / double-oracle loop; deck construction as an RL EDIT policy (not 60 picks from nothing); reward paid by a learned matchup model, grounded with real games each iteration.

| Element | Choice |
|---|---|
| Episode | Start from a deck, apply K edits (K ~ 10-20). Constructive mode from empty only for tabula-rasa experiments. |
| State | Deck card tokens with copy counts; copies remaining per card under the legal pool; meta context = opponent population decks as token sets with mixture weights. |
| Action | Two pointers per edit: remove (over deck tokens), then add (over pool tokens). Masks: 4-copy rule (basic energy exempt), 1 ACE SPEC, >=1 Basic, exactly 60, per-year pool. |
| Reward | Change in predicted win rate vs the meta mixture (dense per edit, telescopes to terminal). A fraction of finished decks scored with real games. |
| Network | Shared card encoder; transformer over deck tokens -> deck vector; attention over opponent deck vectors weighted by mixture -> meta vector; pointer heads score candidates by dot product with a query from (deck, meta, edits remaining). |
| Matchup model | (deck A tokens, deck B tokens) -> P(A wins), cross-entropy on simulated outcomes; REFIT every iteration on real games of the builder's proposals (the builder will exploit model errors). See Section 8 for replacing it with the play value head. |

Outer loop per iteration:
1. Population of decks + matchup matrix (real games under current play policy).
2. Meta-solver -> mixture (diversity choice lives here, Section 7).
3. Builder episodes conditioned on the mixture; sample many; keep top-k distinct by model score.
4. **Pilot** new decks: give the play policy training time on each before trusting its row (an entry is "deck A piloted by this policy").
5. Measure new rows with real games; add; refit the matchup model; repeat.

Compute (40-deck population, 200 games/pair): one new row = 8,000 games; full refresh = 156,000 games. Only new rows per iteration unless the play policy changed enough (re-measure a sample).

Precedents: Q-DeckRec (learned replace-operation deck search), evolutionary deckbuilding in Hearthstone (GA + simulator), deep-surrogate-assisted MAP-Elites for Hearthstone (learned surrogate + quality-diversity).

---

## 7. Diversity under self-play

Why plain self-play collapses: Nash mixtures have small supports; the best response to a mixture is often ONE deck, so populations cycle among a handful of lists; a softmax builder mode-collapses; surrogate errors are attractors. Fixes, in the order to add them:

1. **Meta-solver.** Rectified Nash (PSRO_rN, Balduzzi et al. 2019) trains each best response only against opponents its parent already beats -> game-theoretic niching, provably grows the gamescape. DPP-based diverse best response (Perez-Nieves et al. 2021). For decks, "diverse" = a new matchup ROW that is not a mixture of existing rows (beats a different set of opponents).
2. **Exploiter episodes** (AlphaStar league): some builder episodes target one population deck or a subset -> counter-decks (Garbodor-style) appear, then main-line decks must become robust to them.
3. **Quality-diversity archive** (MAP-Elites) over deck descriptors: energy types, EX count / prize liability, evolution depth, supporter/item counts, average attack cost. Keep the best deck per cell. Doubles as the archetype-rediscovery measurement.
4. **Goal conditioning:** forced core of 1-3 cards, or target descriptor cell. Diversity from the input distribution (reliable) rather than sampling temperature (not).
5. **Best-of-N with a novelty filter:** reject proposals within a card-overlap threshold of existing members.

Track: mean pairwise card overlap, effective rank of the matchup matrix, filled archive cells. Overlap rising + rank stalling = cycling. Apply the same population discipline to the inner-game play policy (pure self-play develops exploitable habits).

---

## 8. Using gameplay knowledge in deck design

The plan in Section 6 uses play knowledge only indirectly (shared encoder + outcomes). Direct mechanisms, most to least principled:

1. **Play value head as the deck evaluator.** The play observation already contains "my remaining deck" and (in a known meta) the opponent's decklist. The value head at turn zero, averaged over sampled opening hands, is a matchup predictor whose target was the game outcome and whose weights were shaped by every mid-game state. Edit reward = change in that value. Caveat: extrapolates for out-of-population decks, so piloting stays.
2. **Cross-attention from candidate card to deck, initialised from the play transformer.** The play encoder learned pairwise interaction functions (Blastoise <-> Water Energy, Rare Candy <-> Squirtle). A deck under construction is another zone of card tokens; candidate scoring = cross-attention from the candidate token to deck tokens with those weights, fine-tuned.
3. **Play-log features on deck tokens.** Per card: drawn / played / searched-for / dead-in-hand-at-end rates, win rate when drawn early. This is the signal that works in practice (17lands' "game in hand win rate" for MTG Limited drives strong draft bots).
4. **Value gradients as an edit prior.** d(value at turn 0)/d(card count) over the vocabulary in one backward pass = first-order "marginal value of one more copy"; a prior for the add pointer, not truth.

Unified version: deck editing as the pre-game phase of the same episode, one network, one reward. Correct but high-variance (each edit credited through a whole game); mechanisms 1-2 are that design with the variance removed.

---

## 9. Roadmap

1. **v4 representation fix (drop-in):** identity-indexed encoder + action mapper + legal mask (Section 4.1). Engine and choice flow unchanged. Confirms that hidden identity was the blocker.
2. **Tokens + pointer heads on the same two decks** (Section 4.2). Must match or beat step 1.
3. **Engine decision for the larger pool:** fork ryuu-play (if targeting 2010-2015 for ground truth) or port its design to Python (if targeting modern cards). Measure ryuu-play's step rate BEFORE deciding (Node 24 is installed).
4. **Ground-truth scaffolding:** per-year legal pools from set codes; implement Black Kyurem-EX and other missing staples; 4 historical archetypes as a fixed population; a deck-general play policy that reproduces the known matchup directions among them.
5. **PSRO loop** with rectified-Nash / DPP diversity, exploiters, MAP-Elites archive (Sections 6-7).
6. **Gameplay-knowledge transfer** into the builder (Section 8); compare against the standalone-surrogate baseline.
7. **Human evaluation** on a ryuu-play server with Legacy-format players (Section 5).

---

## 10. Risks and open questions

- Play strength and deck evaluation are coupled: a weak pilot undervalues setup decks (Blastoise/Keldeo) relative to big-basics decks. The discovered meta reflects the agent's skill ceiling; treat it as a finding, and watch which archetypes appear as play improves.
- Engine bugs become meta bugs. Historical lists double as regression tests.
- ryuu-play throughput is unmeasured; deep-clone per dispatch may dominate.
- Human metas are not equilibria; archetype rediscovery is the robust comparison, meta shares are not.
- v4 has known rule simplifications (KO points instead of prizes; two Lillie's Determination variants keyed on different KO counters).
- The 2010-2015 pool lacks Team Plasma; "Worlds 2013 from scratch" is only meaningful for the buildable subset.

---

## 11. References

- Pokemon_TCG_RL (crystalskies): https://github.com/SuryaSGit/Pokemon_TCG_RL
- ryuu-play: https://github.com/keeshii/ryuu-play ; public server https://ptcg.ryuu.eu/
- MageZero (XMage RL fork): https://github.com/WillWroble/MageZero
- TCG ONE contrib (cards only, engine closed): https://github.com/axpendix/tcgone-engine-contrib ; formats https://tcg.one/formats ; Legacy guide https://forum.tcgone.net/t/legacy-select-format-getting-started-guide/17321
- DeckGym-core (TCG Pocket, Rust): https://github.com/bcollazo/deckgym-core
- Limitless lists: Good 2013 https://limitlesstcg.com/decks/list/3948 ; Altavilla 2014 https://limitlesstcg.com/decks/list/4065 ; Blastoise history https://limitlesstcg.com/decks/25/results
- 2014 Worlds decklists: https://www.pokemon.com/us/play-pokemon/worlds/2014/decks/senior ; 2013 archive https://ptcgarchive.com/2013-decks/
- Worlds 2014 TCG Masters final video: https://www.youtube.com/watch?v=8M6x5JobPtY
- Live battle-log tooling (modern only): https://github.com/kagd/pokemon-tcg-battle-replay ; https://www.ptcglreplay.com/ ; https://www.trainerhill.com/tools/battle-journal
- PSRO survey: https://www.alphaxiv.org/abs/2403.02227 ; Self-Play PSRO: https://arxiv.org/pdf/2207.06541
- Balduzzi et al. 2019, Open-ended Learning in Symmetric Zero-sum Games (rectified Nash): https://arxiv.org/abs/1901.08106
- Perez-Nieves et al. 2021, Modelling Behavioural Diversity for Learning in Open-Ended Games (DPP): https://arxiv.org/abs/2103.07927
- Q-DeckRec: https://arxiv.org/pdf/1806.09771
- Evolutionary deckbuilding in Hearthstone: https://ieeexplore.ieee.org/document/7860426/
- Deep surrogate assisted MAP-Elites for Hearthstone deckbuilding: https://dl.acm.org/doi/10.1145/3512290.3528718

---

## Appendix A: raw probe output (v4, 200 games each)

```
policy=random   decisions=37624  avg turns/game=46.4  avg decisions/game=188
  timing per decision: step=41us legal_mask=6us encode=31us
  max hand=15; hand>12 decisions=16; blind-hand decisions=12011 (31.9%)
    EVOLVE 355, PLAY_POKEMON 2905, USE_ITEM 5662, USE_SUPPORTER 3089
  pending-choice decisions=8611; truncated=647; identities unreachable=348
    ultra_ball_pick 267/1125, fighting_gong_pick 221/579, petrel_pick 94/132,
    night_stretcher_pick 36/279, poke_pad_pick 28/951
  option slots shown=39758, distinct=27783 (30% duplicates)
  win_reason: deckout 138, ko 62

policy=heuristic decisions=14368  avg turns/game=17.0  avg decisions/game=72
  timing per decision: step=39us legal_mask=6us encode=29us
  max hand=37; hand>12 decisions=367 (2.6%); blind-hand decisions=5315 (37.0%)
    EVOLVE 32, PLAY_POKEMON 997, USE_ITEM 2502, USE_SUPPORTER 1784
  pending-choice decisions=3713; truncated=457; identities unreachable=250
    ultra_ball_pick 245/463, fighting_gong_pick 138/194, petrel_pick 32/34,
    poke_pad_pick 26/366, ultra_ball_discard1 7/467, discard2 6/467, night_stretcher 3/117
  option slots shown=18740, distinct=11934 (36% duplicates)
  win_reason: deckout 18, ko 182
```

## Appendix B: scripts (`notes/scripts/`)

- `probe_v4.py`: plays v4 with random/heuristic policies; measures hand-cap hits, choice truncation, blind-hand decisions, timing. Run from anywhere: `py notes/scripts/probe_v4.py` (paths are absolute to this machine).
- `vocab_v4.py`: card vocabulary sizes, search-candidate counts, identity-indexed action-space size.
- `dims_v5.py`: exact state-vector dimensions for the identity-indexed layout (576 lean / 696 full).
- Python: use the `py` launcher (3.14); the `python` alias is the Microsoft Store stub. Set `PYTHONIOENCODING=utf-8` for scripts that print non-ASCII.
