# Metagame RL

A reinforcement-learning project on trading-card-game metagames. The first and main focus is the Pokémon
Trading Card Game (PTCG); other TCGs come later. The roadmap:

1. **July 2000 Super Trainer Showdown** (Pokémon, Base–Rocket): the proving ground (Phase A, now)
2. **Worlds 2005, San Diego** (Pokémon, EX era): a full World Championships metagame (Phase B)
3. **Magic: The Gathering**: a second game, once the approach holds on Pokémon (not started)

The Pokémon environment is
[evcoats/ryuu-play](https://github.com/evcoats/ryuu-play) (branch `sts-2000-pool`), a fork of
[keeshii/ryuu-play](https://github.com/keeshii/ryuu-play), the open-source Pokémon TCG simulator
in TypeScript. The fork is included here as the `ryuu-play/` submodule.

**The goal:** give an agent only a card pool and the rules. It learns to play any deck, learns
to build the decks worth playing, and then is checked against a real historical tournament
metagame that it never saw.

For Pokémon, the end target is a full **World Championships metagame**. The first target is
deliberately much smaller: the **July 2000 Super Trainer Showdown (California)**. It has a 56-card field
that is now fully implemented in the engine and verified. Every part of the system gets built
and proven there first.

## In short

**The approach, in three parts:**

1. **A pilot** (one transformer policy) learns by self-play to play any deck.
2. **A builder** edits decks, judging each one through the pilot's own value and representations.
3. **PSRO** keeps the decks worth playing as an equilibrium mixture, since card metagames are
   rock–paper–scissors rather than one best deck.

The input is only the rules and the card pool: no human decklists, card-specific rules or fitted
priors. The test is whether the result matches a real tournament field it never saw. (Phase A
still has two priors to remove: the builder uses only the 56 cards the field played, and random
starting decks are shaped like human decks, with 16–22 Energy.)

**What is new:**

- **The test is self-discovery.** Does an agent that starts from random decks rediscover what humans
  actually played? Archived lists are used only as the answer key (staples, archetypes, counters),
  never as input.
- **Play and deck building are learned together, by one model.** The builder sees decks the way
  the pilot plays them, so deck quality is defined by play.
- **No prior work combines these for the Pokémon TCG.** We found no published RL work on its deck
  building and play. The closest are surrogate-assisted deck search in Hearthstone and a single
  draft-and-battle policy in Legends of Code and Magic (see the
  [2026-10-06 analysis](notes/analysis-2026-10-06.md)).

**The main lesson so far:** every deck judgment passes through the pilot. A biased or weak pilot
gives a biased or blind builder, so pilot strength is the bottleneck.

## Status

<!-- status:start -->
*Updated 2026-11-07.*

**Where things stand.** A0, A1 and A3 are done, A2 has its ladder and the SimpleBot matrix, and Phase B's engine plays two 2005 lists, while every learned drafting loop has ended with more Energy and fewer Trainers than the 24 human lists, and the ground truth hasn't moved. The pilots' play falls short of a search, which plays PlusPower where their policy gives it about zero, yet under search nearly every Trainer but Professor Oak, Energy Removal and Bill still prices below a basic Energy, and the lists' larger strength gap sits in which Pokémon they run, where a table learned by the loop's own pilots builds strong decks under greedy play but loses its edge under search. In W, the recipe with no table, the draft head learns to cut Trainers, but no head-side change moves the decks' median Trainers off 23, because selection on the loop's own games prices Trainers under Energy and turnover's wide-deck entrants bring the Energy surplus in. That price is the pilot's own and not a matter of search depth, since a two-turn judge keeps the decks greedy keeps, yet the loop's own judge ranks the 24 lists far above its decks and, started from them, holds their counts and improves them, so the strength gap is the loop's search never reaching list-like cards. What drives the Energy-heavy shape is deck-level selection culling Trainer-rich decks, partly because this pilot overdraws them into deck-outs, together with the generator's protected wide entrants and the head's learned Trainer cut, and C205 now tests whether the overdraw is a misplay its own playouts already see.

- **Log #1–504 (A0–A5, B1–B2; rolled up from eight rolled-up summaries).** The engine and environment cover the 2000 field, verified against an oracle and audited against outside card texts and the 2000 rules (faithful apart from minor faults), Phase B's Worlds 2005 branch plays two lists, and the meta level became one learned loop (`rl/metagame.py`: 99 decks sharing one pilot and a draft head, with selection on real results) whose first best decks broke even with the human lists, yet every learned loop, through tournaments, leagues, walls, the round rule and fresh wide decks, ended with more Energy and fewer Trainers than the lists, and the closest shape (round479 with the restored gate, C91) lives in its population rather than its pilot. That lean traced through selection to the pilots, which price the lists' search, disrupt and tempo Trainers below a basic Energy, and no pilot change (memory, cross attention, chain heads, card-token keys, value heads, prompt-answer Qs, training-time branching) fixed it, while a quarantined bench of four human lists showed Computer Search capped by what it fetches and PlusPower a timing failure the pilot can see but doesn't act on. What differs from real play is the games' length: 81-85% of bench games end on the turn cap, and played longer the Trainer-rich lists deck out first and lose to their Energy-heavy copies, so the drafts' Energy lean answers the game these pilots play.
- **Log #505–1016 (A5, from the bench's close to the loop's rainbow Energy; rolled up from eight rolled-up summaries).** The engine reaches human pace when a scripted line plays its speed Trainers, but every drafting lever on the gated base read null or between (per-turn discounts, draft-head entropy, Prize margins, reward changes, practice curricula, powered selection, the pilot's own search in the loop), and a per-card ledger found selection trimming the tempo cards while the draft head proposed them at a quarter of their list share, so nothing in the loop adds them. The price traced to play: the pilot's own search plays PlusPower where its policy doesn't, yet even then the tempo cards only reach parity with a basic Energy and nearly every Trainer but Professor Oak, Energy Removal and Bill prices below one (C135-C143, C165), while the lists' larger strength gap sits in their Pokémon (C167, C169), where a table learned by the loop's own pilots passed C171's gate in evaluation decks but lost its edge under search, and a Trainer table held its decks' Trainers mostly through proposal mass and fell under search (0.351, 0.366 against the lists' 0.505). In W, the recipe with no table, the head learns to cut Trainers but no head-side change moves the median off 23, selection on the loop's own games carries the fall with the Energy surplus entering through wide-deck entrants, and inside the human lists the same pilot prices Trainers under Energy at greedy and one-turn depth and only about level at two turns (C193, C194), with a two-turn judge keeping the decks greedy keeps (C197), which led to C199's off-type Energy test; free RAM was the recurring limit on what ran throughout.

- **Log #1017–1080 (A5, what holds the loop's decks off the lists; rolled up from eight block summaries).** In the loop's own decks the Energy surplus over the lists is all basic Energy, about 1.6 cards of it a rainbow tax and much of the rest Double Colorless replaced by basics, yet under the loop's greedy judge neither on-typing nor denser Energy frees Trainer slots, because this pilot prices a Trainer below a usable Energy in every deck tested, a self-consistent price rather than misplay or an engine fault, and not a Trainer-specific skill gap (specialists help Trainer-poor decks more, C189). A two-turn player values Trainers and Energy efficiency more (C199, C201 under search), but a two-turn judge keeps the same decks as greedy even on the most lists-like population (C202 set 1), and from Energy-light starts both WL seeds' best decks pass the lists' shape at 44 at about 0.15-0.26 of their strength before settling Energy-heavy, so the attractor is the pilot's valuation and the shape match a count coincidence. A long-parked env fault, greedy repeating Charizard's Energy Burn to the turn cap, was found and fixed along the way, touching the loop's rare Charizard decks but not the lists.

- **Log #1081–1088 (A5, WL's search strength, the second loop fault, and C202's fixed reruns).** Under search both WL seeds' lists-shaped best 12 at 44 score about 0.15 against the lists (0.143, 0.154, against the lists' 0.505), so §3's strength criterion fails where its shape criterion holds. A turn-cap check after the Energy Burn fix found 4 of 2,000 greedy games still capped by Powers that cycle state (Energy Trans, Damage Swap), none of them in the lists, and a second rule, no Power whose trial repeats a state already seen this main phase, was built, tested and made live after C202's reruns, with C189 stage 3 held until then so its specialists share one env. C202's sets rerun under the fixed env, and the sets finish with medians that miss both bands and means that show no judge effect.

- **Log #1089–1096 (A5, C202's close, A177's C203 and the frozen-head check).** C202 closes with no judge effect on the means at either set, so a deeper judge doesn't change which decks are kept on any population tested, and under both env fixes no greedy game hits the turn cap; no deep round is run, its topics being covered. On the auditor's A177, C203 (a) drops the 24 lists into W's own populations and 19-22 of them rank in the top quarter under W's own pilot at both seeds (R-explore-a), so the loop's judge would keep the lists and the strength gap is its search over card content. A look-back on a frozen-head fault found in C203 (b)'s smoke (a saved Adam lr restored) found no past read affected, H0's head hash being unchanged from 0 to 44.

- **Log #1097–1104 (A5, C189's close and C203's lists-start).** C189's third stage finds no Trainer dividend on W s48's decks either (R-no-bias sampled), so at neither W seed does a Trainer-specialized pilot lift Trainer-rich decks. C203 (b), started from the 24 lists with W s48's pilot and head frozen, holds their Energy (−0.08 over 7 iterations) and improves them by its own head to head (evolved top 12 against the originals 0.566), so the loop's judge keeps and refines list-like decks. On the auditor's review that read is "no shift in 7 iterations, turnover off", and (b3) was designed to run the lists-start with turnover on, W's 20-iteration protection kept and the lists started at age 20, for 30 iterations, to tell whether the entrant generator holds the minimum or the search's start and reach do.

- **Log #1105–1112 (A5, C203's replicate and turnover-on read, and C204's design).** C203 (b) replicates at W s49: from the lists, frozen selection holds their Energy (+0.33) and improves them (G3 0.594 against the originals), though W s49's learned out-cut moves about 2 Trainers into Pokémon. With turnover on, (b3)'s interim read shows the pump: the lists' Energy rises +2.4 in 14 iterations, 62% of it from turnover's kill of Trainer-rich, Energy-light lists and 23% from the generator's dilution, so the loop's deck-level ranking under this pilot penalizes Trainer-rich decks, lists included. C204 was then set to find how those culled lists lose, with the auditor's time-win worry answered from the sourced STS rule (a time-win 2 of 3 points) and kept as a sensitivity read, and its replay confirmed z is the round rule exactly.

- **Log #1113–1120 (A5, overdraw among the lists, and C205's design).** C204 finds the Trainer-rich lists turnover culls deck out far more than the kept ones under this pilot (2.7× under W s48's, 1.66× under W s49's: R-overdraw at one pilot, the direction replicated), drawing more a turn and ending with less deck, while W's own culls lose the same ways as its kept decks; rule 9 is clean, and counting time-wins as full wins barely moves the cull. The pilot sees both players' exact deck counts, so the overdraw isn't forced by missing input, and C205 was set to ask whether it's a misplay at low deck, with both pilots and a dose-response over four deck-size buckets; its timed pilot hints so (playing draw at 10 or fewer cards left loses 0.13 by the pilot's own follow-up, at a flat 0.17 play rate).

- **Log #1121–1128 (A5, (b3)'s close, the overdraw test and the clock question).** C203 (b3), the lists started with turnover on for 30 iterations, reads between: Energy rises +2.6 from turnover's kill (+2.1) and protected wide entrants (+1.6), with the lists' lineages losing 6 Trainers to the head's cut, so the Energy-heavy attractor comes from deck-level selection, the generator's protected entrants and the learned Trainer cut. C205 then finds this pilot plays draw cards as often at 10 cards left as at 40 while its own playouts say stop, at both pilots, and the auditor's question whether the turn clock prices Trainers down was answered from C113's earlier read: played longer, the lists lose more to their Energy copies because they deck out first, so the clock props their Trainers up.

**Recent (log #1129–1130).** C205 reads R-misplay under both pilots: at deck ≤ 10, playing a draw card loses −0.05 to −0.07 by the pilot's own follow-up, rising with cards left at about +0.0026 a card, while its play rate doesn't adapt, although it sees the exact deck count. C206, an evaluation-only test with draw plays withheld at low deck, now asks whether a pilot that didn't overdraw would price the lists' Trainers at Energy, before any learned fix is built; it waits for the GPU, which Evan's apps fill, and the ground truth hasn't moved. The pilot almost never feels a deck-out in training (1.6-1.9% of its games end that way), so if C206 shows the overdraw moves the price, the fix is exposure to games that reach low decks, not a new value head.

The full record is in [`notes/progress-log.md`](notes/progress-log.md).

**Next:**

1. C199: the two-turn cells (setA-h2 running, then setB-h2), then the rule-9 replay with per-seat counts (starvation against misplay, research's split in #1018), then arm (c) under greedy and two-turn search on (a)'s deals, read as (c) − (a).
2. C189, the specialist pilot on Trainer-rich loop decks (SH, SL, cells), after the rule-9 read; its hold keeps a slot for its stages.
3. C200's lever, research's call: the in-choice for an on-type fix (R-not-proposed), any change rules-derived and under its own record; `wide_deck` is not to be fixed by hand.
4. Waiting behind C189's hold and RAM: C197's C49-sd column, WL s52's resume to 74 and WL s53's, WR s50 (paused), H0 s49, C184's ND s49.
5. Evan's rulings, only if still needed: practice decks selected on named draw copies (#726) and research's standing-rule question (#723, #732); the `ar/` re-setup after the `rl/` and `env/` changes.
<!-- status:end -->

---

## The problem: three decisions stacked

| Level | Decision | Horizon | Learned by | Signal |
|---|---|---|---|---|
| **Move** | Which card, which target, which search pick | One prompt | Policy network over the legal candidates | Policy gradient and value from the game level |
| **Game** | How to pilot a fixed 60-card deck under hidden information | ~135 actions per game in this format | Self-play against a population of opponents | Win or loss |
| **Metagame** | Which deck to bring, given what everyone else brings | One tournament field | A deck-edit policy inside a PSRO loop | The matchup table produced by the game level |

Card metagames are non-transitive (rock–paper–scissors on top of raw power), so the target at
the top level is an **equilibrium mixture of decks, not one best deck**. The three levels are
coupled: play skill decides which decks look good, and the decks in the field decide which
play skills matter.

**Ground truth.** Archived tournament results are the answer key. The agent drafts its own meta
from random decks on the full card pool and never sees the archived lists; its meta is what it
knows about decks. An agent that lands on what humans actually played has shown something that
win rates against its own checkpoints cannot. Human metagames are not equilibria, so matching
meta *shares* is not the goal. The comparison has three tiers (`rl/answer_key.py`):

1. **Staples:** cards nearly every top deck plays, at near-fixed counts. In the 2000 field,
   Professor Oak is in 24 of 24 lists, and Double Colorless Energy, Gust of Wind and Computer
   Search in 23. These hardly depend on the opponent, so the agent's decks should agree even
   where the archetype mix differs. Scored by inclusion, and by count within one copy. Staples
   such as Gust of Wind and Energy Removal only earn their slot under a pilot that uses them
   well, so this tier also tests play.
2. **Archetypes:** does each archived archetype appear in the agent's equilibrium support, by
   card overlap with the archived lists?
3. **The meta:** the counter table (each deck's best counter, with its win rate and how
   exploitable the deck is) and matchup directions, checked against era write-ups.

---

## Why start in 2000

| | July 2000 STS (Base–Rocket) | Worlds 2005, San Diego (EX Ruby & Sapphire–EX Emerald) |
|---|---|---|
| Card pool in ryuu-play | **Complete**: every card in the field is implemented and verified | Partial: 3 of the 9 EX sets are in the engine (not yet verified); about 100 of the 139 card names in the season's archetype lists still need an implementation (see B1) |
| Distinct cards in the field | **56** (21 Pokémon, 26 Trainer, 9 Energy) | 139 card names across 19 archetype lists; nine EX sets plus POP Series 1 and promos in the format |
| Evolution | Three stacks in the whole field, max depth 2 | Deep lines, Rare Candy, many evolution engines |
| One player's full observation | **482 bits ≈ 60 bytes**; ~760–870 floats one-hot | Needs the scalable token representation |
| Recorded field | 24 top-8 lists across three age divisions | One archived list per archetype so far (ptcgarchive) and the four official 2005 World Championship decks; full top-cut lists not yet sourced |
| Mechanics | No abilities-era complexity, no EX/GX prize rules, no ACE SPEC | Poké-Powers and Poké-Bodies, Pokémon-ex (two Prizes), Dark Pokémon; all already in the engine. No ACE SPEC, no Lost Zone, no LEGENDs |

The 2000 format is small enough to iterate on in hours on one machine and real enough to have
an answer key. Its weakness is also clear: there is **one** recorded field, and it is
concentrated (Wigglytuff 10/24, Haymaker 7/24, 8 archetypes). It can answer "does the agent find
Wigglytuff and Haymaker?" well. It cannot validate a predicted distribution. That is why it is
the proving ground and not the end result.

**The rule for Phase A:** anything that must scale to Worlds (the token representation, the
deck-general policy, the PSRO loop, the evaluation protocol) gets proven on 2000 first, against
a simpler baseline it must match or beat.

---

## Plan

### Phase A — Proving ground: July 2000 STS California

#### A0. Engine covers the field — ✅ done

On the engine fork, branch `sts-2000-pool`:

- Fossil Ditto re-enabled, and its two open TODOs closed (copying passive Pokémon Powers, and
  offering copied in-play Powers). Mr. Mime's Invisible Wall and Muk's Toxic Gas now work
  through Ditto.
- A new Wizards Black Star Promos set with the two promos the field played: Mewtwo #3 and Mew #8.
- **Verification:**
  - All 24 archived decklists build and start a game.
  - 541 engine specs pass (25 new).
  - 68/68 targeted card-interaction tests pass.
  - 1,926 card-data field checks against pokemon-tcg-data, with 1 cosmetic mismatch.
  - 22/23 dated 2000-era rulings pass. The failure (T18, Mysterious Fossil as a starting Basic)
    doesn't affect this field.
- **Measured:**
  - The engine runs ~9 real games/s per core and scales near-linearly to 8 workers.
  - No first-player bias is detectable (seat A won 54.5% ± 5.8 over 288 mirror games).
  - SimpleBot, the bundled bot, costs ~30× the engine per move (0.6 games/s/core), so it is an
    evaluation floor, not a self-play opponent.

#### A1. Make the engine an RL environment — ✅ done

The engine was built for a websocket server, not for millions of headless games. It has no
legal-move enumerator: an illegal action throws, and the store restores a deep-cloned backup.

1. **Throughput fixes — ✅ done** (fork `888b385`).
   - Stop deep-cloning `state.logs` on every dispatch. It grew all game long, which made a game
     O(n²) in its length.
   - Cache the card order in `propagateEffect`, rebuilding it when a new card appears.
   - Measured **554 → 160 µs/action (3.5×), 18.7 → 64.6 engine-only games/s/core**, with the
     state identical to the old engine after every action over 300 seeded games
     (`notes/scripts/ryuu_engine_equivalence.js`).
2. **Legal-action enumerator — ✅ done** (`env/legal.js`). At every decision, list the candidate
   actions: play card, attach, evolve, retreat, use Power, attack, pass, and the options of
   every open prompt. Verify it against the engine: every enumerated action must be accepted,
   and a sampled non-enumerated action must be rejected. Verified against an exhaustive oracle
   (`env/oracle.js`) on every decision of 10,000 games: 0 mismatches.
3. **Observation encoder — ✅ done** (`env/encode.js`): 1,110 byte-exact features (12 slots ×
   54 plus hand, discards, unseen cards, counts) and 1,915 action ids. Hidden information stays
   hidden: the opponent's hand shows as a size, and prizes are unknown to both players.
4. **Environment API — ✅ done** (`env/env.js`): `reset(deckA, deckB, seed) → obs, legal` and
   `step(action)`. Seeded, so games replay exactly. Each worker process runs many games
   (`env/runner.js`).
5. **Training bridge — ✅ done.** *Decision:* rollouts in Node with ONNX inference
   (`env/rollout_worker.js`), training in PyTorch (`rl/train.py`), syncing weights each
   iteration.
6. **Housekeeping — ✅ done.**
   - Fix T18 (fork `fc4c8ec`, `Rules.fossilsAsStarters`).
   - Run the spec, interaction, rulings and decklist checks as CI (`.github/workflows/ci.yml`),
     plus the engine equivalence, env and enumerator checks.

**Exit:** a seeded, enumerated, encoded environment at ≥ 50 random-policy games/s/core, with
the enumerator verified on every action across ≥ 10k games. *Met: 0 mismatches over 10,000
games; 53.9 random-policy games/s/core (`env/tools/bench_env.js`).*

#### A2. Baselines and the evaluation ladder

- **Opponents:** random, a cheap heuristic bot, SimpleBot (floor), and a fixed-budget search
  bot as a relative scale.
- **Protocol:** every comparison is seat-swapped, with fixed decklists and confidence intervals.
  At 200 games the standard error is ~3.5 points.
- **Puzzles:** positions in this format with provable answers, such as lethal this turn,
  avoiding deck-out, and the right Energy Removal target.
- **Skill-ceiling baseline:** the full 24 × 24 matchup matrix and its Nash equilibrium **under
  SimpleBot**. This is the reference for how the discovered meta shifts as play improves.

#### A3. Game level, one matchup — ✅ done

PPO with a small self-play league, on the field's top two archetypes (Wigglytuff vs Haymaker),
using the identity-indexed encoding from A1.

**Exit:** beats SimpleBot by a clear, seat-swapped margin in both directions of the matchup, and
the result holds against held-out league checkpoints, not only its training opponents.

#### A4. Game level, every deck

1. **One deck-general policy**, conditioned on its own decklist and the opponent's, trained
   across all 24 archived lists.
2. **The scalable representation**, built here and required to match A4.1 before Phase B: card
   tokens, a verb head plus a pointer head over the legal candidates, and card embeddings built
   from card features and rules text.

**Exit:** beats SimpleBot with every deck; the trained-policy matchup matrix is stable across
reruns; and its matchup directions agree with era write-ups wherever those exist.

#### A5. Metagame level

![The A5 PSRO loop: population and real-game matrix, Nash, matchup model, swap search, confirmation with real games, piloting; each step marked built, partly built or planned](notes/schematics/metagame-builder.svg)

*The loop as of log #28 ([full page](notes/schematics/metagame-builder.html)). Since log #34, step 4 in the code is the restart search of `rl/search.py` (`rl/psro.py --builder games|model|value`); the PPO edit policy remains as `--builder edit`. Since log #65 the code is one loop instead (`rl/metagame.py`: per-agent draft heads trained on game results, `rl/draft.py`); the PSRO builder is at the `pre-simplify` tag.*

1. **Fixed population.** Nash over the trained-policy matrix of the 24 archived lists. Do
   Wigglytuff and Haymaker sit in the support? Compare against the SimpleBot equilibrium from A2.
2. **Deck builder: PSRO with a matchup model.** A deck population, its real-game matchup
   matrix and its Nash mixture. Each iteration:
   1. Solve Nash over the population's real-game matrix.
   2. Search card swaps (under the construction rules), ranked by the matchup model's predicted
      win rate against the Nash mixture, from several starting decks.
   3. Play real games for the top few candidates, add them to the population, refit the model.

   - **The matchup model** predicts P(A beats B) from both decks (mean of the token model's card
     embeddings, so unseen cards are covered) plus the pilot's value at the start of the game,
     v(A, B), averaged over ~16 opening hands (forward passes, no games). The value feature
     starts the model at the pilot's own judgment; it learns where the pilot is wrong, mostly on
     decks the pilot has not trained on. It is fitted on every real game played so far, and only
     ranks: every number that enters the matrix is from real games.
   - **Exploration**, by two mechanisms:
     - **Random restarts with varied edit budgets.** Each search starts from a fresh random
       legal deck or from a support deck, with a budget, drawn per search, on how many cards it
       may change: from 8 (refining a support deck) to 60 (a full rewrite). This decides where
       the search looks: many separate basins rather than one deck refined forever.
     - **Optimism under uncertainty.** The matchup model is a small ensemble (about 5, trained
       on resampled games), and candidates are ranked by mean + β × spread. Where the copies
       disagree is where the model has seen few games, so unusual decks get tried, and the bonus
       shrinks once their games are in. This decides which candidates get real games.
     - A new deck joins the population only if it differs from every existing deck by at least
       ~10 cards, so the population does not fill with near-copies.
   - **Is exploration working?** Cold starts from different seeds reach overlapping supports (by
     card overlap); new decks keep entering the support, and the share of the pool tried keeps
     growing; and the model's error on newly tested decks stays small. Disagreeing seeds with a
     stalled support mean explore more.
   - New decks get piloting time before their matchup row is trusted.
   - Left out unless plain search stops finding new support decks: an RL-trained edit policy,
     MAP-Elites, a rectified-Nash solver, exploiter episodes.
3. **Two pool sizes.** Develop on the 56 cards the field played, which leaks human card choice
   but is cheap. Make the actual claim on the **full legal Base–Rocket pool** (all legal promos
   are now in: Wizards Black Star Promos #1–#16, fork `64330a4`). Most of those ~233 cards are
   unexercised by tests, so a cold-start builder will find engine bugs and treat them as
   strategies; expand verification first.
4. **Counters.** For every deck in the agent's population, its best counter and that counter's
   win rate (the deck's exploitability), from the matchup matrix. Then a counter-deck search:
   the builder aimed at one opponent deck instead of the meta mixture, over the whole pool, with
   the matchup model proposing and real games confirming. It answers "what beats X best?",
   possibly with a deck no one played. The archived decks are also scored as held-out entries
   against the agent's equilibrium: how would each human list have fared in the agent's meta?

**Exit:** from a cold start on the full pool, scored with the three-tier answer key: the agent's
mixture plays the field's staples at near-field counts, archived archetypes appear in the
equilibrium support (by card overlap), and the counters and matchup directions agree with era
write-ups where those exist. The result replicates across seeds. The three age divisions serve as
rough replicates of the human field.

#### A6. Play knowledge feeds deck building

- Measure what the play network's start-of-game value adds to the matchup model (A5.2): the
  model with and without it, scored by prediction error on newly tested decks, and the value
  alone as the ranking.
- Reuse the play encoder's card-interaction weights to score candidate cards.

**Phase A exit gate**, all required before starting Worlds work in earnest:

- The token-pointer policy matches the identity-indexed one.
- Cold-start rediscovery succeeds on the full pool.
- The evaluation protocol and environment run unattended.

---

### Phase B — Full Worlds metagame

Phase B reuses everything from Phase A. What is new is the card pool, the scale, and the data.

#### B1. Target: Worlds 2005, San Diego

The 2005 World Championships (San Diego, August 19–21, 2005) were played in the Modified format:
EX Ruby & Sapphire, Sandstorm, Dragon, Team Magma vs Team Aqua, Hidden Legends, FireRed &
LeafGreen, Team Rocket Returns, Deoxys and Emerald, plus POP Series 1, the EX Trainer Kits and
Nintendo Black Star Promos 1–27. Wizards' four 2005 World Championship decks reproduce top
players' lists: Queendom (Jeremy Maron), Dark Tyranitar (Takashi Yoneda, a finalist), King of the
West (Michael Gonzalez) and Bright Aura (Curran Hill).

Chosen by measurement over Worlds 2011 (San Diego) and 2013–14. The card gap is about the same as
2011's, and 2005 needs no new engine mechanics.

- **Coverage, measured** (`notes/scripts/ryuu_coverage_season.py`, results in
  `notes/data/eval/coverage_2005.json` and `coverage_2011.json`; every card resolved to its
  printing through pokemon-tcg-data):

  | | 2005 | 2011 |
  |---|---|---|
  | Archetype lists (ptcgarchive) | 19 lists, 139 names | 13 lists, 111 names |
  | Names still to implement | ~100 (72%) | ~79 (71%) |
  | Copies buildable today | 362 of 1,140, +65 near-reprints to check | 334 of 780 |
  | Closest list | Zapdos/Moltres "Birds" 40/60 | Reshiram/Typhlosion 42/60 |
  | Full legal pool | 3 of 9 EX sets present, ~600 cards to go | ~35 cards of 6 sets present, ~600 to go |
  | New engine mechanics | none | Lost Zone, LEGEND cards |

  No list in either season is fully buildable yet. The most-played missing 2005 cards are
  Supporters and Trainers from the missing sets (TV Reporter, Steven's Advice, Rocket's Admin.,
  Swoop! Teleporter), Jirachi (Deoxys) and the Team Rocket Returns Dark Pokémon. "Different"
  (same name, different card) slightly over-counts, since a few are wording-only changes.
- **The engine's EX sets:** Ruby & Sapphire, Sandstorm and FireRed & LeafGreen are
  near-complete (about 109, 98 and 112 cards) but not yet checked against card data and
  rulings as the 2000 pool was.
- **2013–14, for comparison:** two archived Worlds Blastoise/Keldeo lists build 57 of 60 cards,
  but all of Team Plasma and Black Kyurem-EX are missing (`notes/tcg-rl-research-notes.md`).
- **Data:** the season's archetype lists (ptcgarchive, saved in
  `notes/data/2005-season-ptcgarchive/`) and the World Championship decks. Full Worlds 2005
  top-cut lists and placements are still to be sourced.
- **Legality:** build the 2005 legal pool from set codes. The current pool mixes sets that never
  coexisted, and an agent would invent decks no one could have played.

#### B2. Close the card gap with the Phase A verification pipeline

For every new card: card-data checks against pokemon-tcg-data, dated rulings tests, targeted
interaction tests, and every archived Worlds list as a regression deck.

#### B3. Scale

- The token representation carries over unchanged.
- Re-profile the engine on the larger pool and rerun the throughput budget before sizing PSRO.
  At 200 games per pair, one new row in a 40-deck population costs ~8,000 games.

#### B4. Game level, then metagame level on the Worlds pool

Same exit criteria as A4 and A5, measured against the archived Worlds top cut.

#### B5. Human evaluation

- Run the agent on a ryuu-play server against players who know the era (TCG ONE's Legacy format
  covers this pool).
- Use fixed archived lists, seat-swapped, ~200 games per opponent pool.
- The defensible claim is "beats experienced players on fixed lists within this pool."

---

## Risks

- **Play skill and the meta are coupled.** A weak pilot undervalues setup decks. Which
  archetypes appear as play improves is tracked as a result in its own right.
- **Engine bugs become meta bugs.** Archived lists double as regression decks, and the builder
  is only let loose on cards with test coverage.
- **One field in 2000.** The STS gives a single 24-deck field (STS New Jersey is a Gym-era format
  needing two unimplemented sets, 0/24 buildable). Phase A success means yes/no rediscovery,
  not distribution matching.
- **Human metas are not equilibria.** Rediscovery is the comparison; share percentages are not.
- **Worlds coverage.** "From scratch" claims in Phase B hold only for the buildable pool until
  B2 closes the gaps.

---

## Repository

| Path | Contents |
|---|---|
| `ryuu-play/` | Submodule: the engine fork, pinned to a commit on `sts-2000-pool`. Engine changes are committed there and the pin is bumped here. |
| `notes/progress-log.md` | Append-only log of finished todos, from which the Status section is summarized |
| `notes/analysis-2026-10-06.md` | Analysis of logs #30-42 with a literature survey and the ranked next steps |
| `results/` | Headline results, one folder each with a README, data and the scripts to reproduce them ([index](results/README.md)); [2000s result #1](results/2000s-result-1/) is the A5.2 builder comparison |
| `notes/schematics/` | Diagrams of the system, as standalone HTML pages: `metagame-builder.html` (and the `.svg` shown under A5) is the A5 PSRO loop, marked built vs planned |
| `env/` | The RL environment: seeded game loop, legal-action enumerator and its oracle, encoder, env API, rollout runner and workers; `env/tools/` has the verification, test, benchmark and evaluation scripts |
| `rl/` | The learner: PyTorch models, ONNX export, rollout reader, PPO training (`python -m rl.train`) |
| `notes/tcg-rl-research-notes.md` | The research log and RL design, including the comparison with [Pokemon_TCG_RL](https://github.com/SuryaSGit/Pokemon_TCG_RL) (v4) |
| `notes/three-level-rl-pitch.md` | The three-level (move / game / metagame) pitch |
| `notes/sts-2000-engine-check.md` | The 2000 verification report: coverage, throughput, profiling, state vector |
| `notes/data/` | The archived STS decklists (scraped from ptcgarchive.com), aggregated to CSV and JSON |
| `notes/scripts/` | Harness, verification and measurement scripts (Node for the engine, Python for scraping and card-data checks) |

`notes/data/cache/` (raw scraped pages and the pokemon-tcg-data download) is not committed;
`meta_aggregate.py` and `ryuu_card_data_check.py` rebuild it on first run. The three
`*_v4.py` / `dims_v5.py` probes expect a local Pokemon_TCG_RL checkout at a hard-coded path.

### Setup

Requires Node.js 18.19+ (developed on Node 24).

```
git clone --recurse-submodules https://github.com/AI-Alignment-UIUC/metagame-rl
cd metagame-rl/ryuu-play
npm install --workspace=packages/common --workspace=packages/sets --workspace=packages/simple-bot
npm run compile -w packages/common && npm run compile -w packages/sets
(cd packages/sets && npx jasmine-ts "tests/**/*.spec.ts")      # 541 engine specs
cd ..
node notes/scripts/ryuu_sts_decks_check.js        # 24/24 archived decks build and start
node notes/scripts/ryuu_rulings_tests.js          # 22/23 (T18 open)
```

The scripts find the engine at `ryuu-play/` by default; pass a path or set `RYUU_PLAY` to
point them elsewhere.

The environment and training (from the repository root):

```
npm install                                        # onnxruntime-node for the rollout workers
node env/tools/test_env.js                         # env API and encoder
node env/tools/verify_enumerator.js --games 200    # enumerator vs. the oracle
node env/tools/bench_env.js                        # random-policy games/s on one core
node env/tools/evaluate.js --x simplebot --y random --games 200
py -3 -m venv .venv && .venv/Scripts/pip install torch numpy onnx   # (CUDA build of torch from download.pytorch.org)
.venv/Scripts/python -m rl.train --run runs/try --matchup "Wigglytuff|Haymaker" --both-directions
```

## Credits

The engine and the ~900 card implementations are by keeshii and the ryuu-play contributors
(MIT). Card data was checked against
[PokemonTCG/pokemon-tcg-data](https://github.com/PokemonTCG/pokemon-tcg-data). Tournament data
is from [ptcgarchive.com](https://ptcgarchive.com/).
