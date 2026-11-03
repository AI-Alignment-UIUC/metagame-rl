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
*Updated 2026-11-02.*

**Where things stand.** A0, A1 and A3 are done, A2 has its ladder and the SimpleBot matrix, and Phase B's engine plays two 2005 lists, while every learned drafting loop has ended with more Energy and fewer Trainers than the 24 human lists, and the ground truth hasn't moved. The pilots' play falls short of a search, which plays PlusPower where their policy gives it about zero, but under search the tempo cards only reach parity with an Energy, nearly every Trainer but Professor Oak, Energy Removal and Bill prices below one, and the lists' larger strength gap sits in which Pokémon they run. Tables learned by the loop's own pilots on rules-only decks build strong decks under greedy play, but the Pokémon table's edge over the lists' own goes under search, and the Trainer table's decks fall under search (0.351, 0.366 against the lists' 0.505), rediscover 1 and 0 of 8 archetypes, and held their Trainers mostly because the bonus raised Trainers' proposal mass. The sharper target from Evan's GPU pause is that in W, the recipe with no table, Trainers fall because the out-choice comes to prefer them (1.02, 1.04 to 1.31, 1.42 times their share of copies, on samples) with incoming mass flat. On his resume a mass-neutral table (DN, neutral D, against WR and W) and a frozen head (C187's H0), both built and passing their CPU checks, run first.

- **Log #1–504 (A0–A5, B1–B2; rolled up from eight rolled-up summaries).** The engine and environment cover the 2000 field, verified against an oracle and audited against outside card texts and the 2000 rules (faithful apart from minor faults), Phase B's Worlds 2005 branch plays two lists, and the meta level became one learned loop (`rl/metagame.py`: 99 decks sharing one pilot and a draft head, with selection on real results) whose first best decks broke even with the human lists, yet every learned loop, through tournaments, leagues, walls, the round rule and fresh wide decks, ended with more Energy and fewer Trainers than the lists, and the closest shape (round479 with the restored gate, C91) lives in its population rather than its pilot. That lean traced through selection to the pilots, which price the lists' search, disrupt and tempo Trainers below a basic Energy, and no pilot change (memory, cross attention, chain heads, card-token keys, value heads, prompt-answer Qs, training-time branching) fixed it, while a quarantined bench of four human lists showed Computer Search capped by what it fetches and PlusPower a timing failure the pilot can see but doesn't act on. What differs from real play is the games' length: 81-85% of bench games end on the turn cap, and played longer the Trainer-rich lists deck out first and lose to their Energy-heavy copies, so the drafts' Energy lean answers the game these pilots play.
- **Log #505–568 (A5, pace, the bench's close and the first drafting levers; rolled up from eight block summaries).** The engine reaches human pace when a scripted line plays its speed Trainers (a median 9 own turns when its pieces come together; corrected at log #606-607: the pilots' 19-32 counted only six-Prize wins, and on wins of any ending a pilot is only about 3 own turns slower uncontested, 14 against 11), but in the pilots' long games holding Professor Oak and Bill is right, and neither a per-turn discount (BENCH-P9) nor forced Trainer plays (BENCH-P10) moved the speed Trainers' play or the lists' value, so with two audited card faults fixed drafting resumed from the gated base, whose nine seeds sit 11.9 ± 4.2 from the lists' shape with 2.1 ± 0.4 tempo-card copies a deck against the lists' 9.2. The first drafting levers left that gap almost whole: search continuations and search-priced Trainer play read not-conversion and between, more drafting iterations read flat, and the per-turn discount in the drafting loop met its four-seed queue gate by 0.02 (2.56 copies) but is not a replicated effect by the null rule (the replication seeds alone +0.9 SE), and shape didn't move. In all 18 engine-K seeds the loop's own selection accepts moves with fewer Trainers and more Energy than its draft head proposes, so the loop's games themselves price Trainers under Energy, and the queue runs a stronger discount (C124), more draft-head entropy (C126), then the discount continued (C125).

- **Log #569–632 (A5, the drafting levers, the selection ledger and PlusPower's price; rolled up from eight block summaries).** Every drafting lever tried after the first round read null (a stronger per-turn discount, more draft-head entropy, the discount continued, Evan's Prize margin in selection, sooner-win and lower clock payouts in the pilot's reward, and the pilot's own search playing the loop's games), and a per-card selection ledger (C127, its lean stable across four seeds, C129) found the tempo four's deficit on both sides: selection trims them by about 0.07 copies a move and the draft head proposes them at a quarter of their list share, so nothing in the loop adds them, and single seeds' shapes wander like a random walk (C125), so only replicated effects count. The cause traced to play rather than reach or the field: the loop's field offers the lists' knockout chances (C134), and the pilot's own full-width search, scored by its value, plays PlusPower at 83% of exactly-10-HP breakpoints against greedy play's 0.4% (C135), because the policy puts about zero probability where a fast line plays it (C133), while on wins of any ending the pilot is only about 3 own turns slower than a script uncontested (corrected at #606-607). Fixing the play doesn't reproduce the lists, though: priced against its Energy copy, PlusPower goes from below an Energy under greedy play (−0.054 a deal against the California field, in all 19 lists) to parity with both seats searching (C136, C139), never above, while distilling the search into the policy failed in expert iteration's fourth form (C137) and searching in the loop didn't speed its games (C138).

- **Log #633–696 (A5, PlusPower's parity, the Trainer groups, and deep round 7's orthogonal levers; rolled up from eight block summaries).** Under the pilot's own search PlusPower and the tempo package price at about an Energy against the California field at every clock, scorer and strength tried (C140-C143), while the draw group beats an Energy for arm 0 (C144), the first positive anchor, a skill that came from arm 0's practice on human lists (C146) and that the loop's own pilot, generally weaker on coherent decks (0.391 head to head, C147), and its drafted decks give much less (C145). Deep round 7's orthogonal records on Evan's row 116 then read null throughout: selection's 1 SE winners re-test at chance (C151), pooled Thompson proposals slid into Pokémon piles (C150), count features' draw gain was training noise (C152, C152b) and the pilot's early value is no cleaner a card signal than the outcome (C154), while C149's mirror update failed acceptance on a seat-flip bias and C153 was cancelled on auditing's power check. Along the way three pipeline faults were caught before they cost a result (a cp1252 deck-file decode, a launcher rule that refused a second seed, a pilot that couldn't load grown weights), and one incident of mine let cancelled jobs run without affecting any result.

- **Log #697–760 (A5, powered selection, draw skill, and where the lists' strength sits; rolled up from eight block summaries).** Practice on the population's decks, concentrated practice and powered selection left the ground truth where it was: powered selection's kept moves are real (78% hold up on held-out games) but lean to shape and arrive too slowly, about 0.25 moves an iteration, draw-rich practice is only a lead, and neither card-neutral curriculum nor the pilot's own search can aim practice at the draw cards (C148, C155-C161). Draw's gap between the lists and rules-only decks was largely how it was measured (+0.077 against +0.027 under one swap, +0.023, SE 0.014, with the lists' extra Energy allowed for; C163, one pilot), and a factorial table of all 42 Trainers reads between: under all four pilots Professor Oak beats a basic Energy, Energy Removal and Bill slightly, and nearly every other Trainer loses to one, so the table doesn't lead to the lists' 28 Trainers and C166 closed on its gates (C165). The lists' much larger strength gap sits in their Pokémon and Energy, not their Trainers (Body +0.28 against Trainers +0.04 to +0.06 across four pilots, C167, its replication post hoc), the fit's Pokémon names carry most of it, and C168, the first long fresh run with and without immigration, is built with a stop for the walls, since the long line's oldest decks are Snorlax and Chansey walls whose Trainer match isn't rediscovery.

- **Log #761–824 (A5, the Pokémon table, and what search and strong bodies do to the Trainers' price; rolled up from eight block summaries).** Which Pokémon a deck runs carries the lists' body gap (C169), and a table learned by the loop's own human-free pilots on rules-only decks passed C171's whole gate on plain tables at κ 3 (Y − G on the lists +1.16 and +1.40 logit), the first human-free signal shown in games to do so, but only in evaluation decks: C172 pooled R-easy-to-pilot and under search C173's stage A read unresolved with the lists' own Pokémon moving up against it at all four readings, so its drafting run holds and `chosen.json` stays unwritten. The current recipe without the table slid to Energy by W s48's iteration 53-54 (G1 10.97 at 29 to 19.5, median Trainers 28 to 23), with no pilot spiral behind it (R-no-spiral at both nets), and free RAM set the order of runs throughout, stopping W s49 twice. The Trainers' low price doesn't belong to weak games on the evidence so far: C175 reads R-not-context on one seed (Y − G −0.0041, E2 − G −0.0053, SE 0.0010 and 0.0013) and its common field shows no rise either, and full width's search reads R-trainers-flat on seed 48's 12 pods (+0.0012, SE 0.0008, 15% of the gap), leaving a post hoc lead in the lists' top 12 (+0.0027, SE 0.0008) that seed 49's replication, written first, now tests.

- **Log #825–888 (A5, full width's close, overdrawing, and the Trainer table's first run; rolled up from eight block summaries).** Full width's search closed flat on both seeds (+0.0012, −0.0010), W s49 repeated W s48's slide on the current recipe and lost its G3 rise under search (0.374 to 0.236, one seed), and the lists scored 0.502 on G3's design and 0.505 under search, with RAM the recurring limit on what ran. What the lists gain by shedding under greedy human-free pilots is largely overdrawing their own decks (the last draw at a deck of 10 or under in 84-88% of those games, 53% under arm 0), removing deck-outs takes most of that gain and of the pilot gap, and M's practice on draw-selected rules-only decks reaches arm 0's level mostly as deck discipline, whether that selection is human knowledge waiting on Evan (#726). The plain Trainer table on the drafter's picks (C182's D) started at G3 0.427 without deck-outs and read between at 44, far from W on shape, with deck-outs turned on in its own games (34.5% against W's 1.4%), about 0.07-0.09 of its strength being the judge, and strength and Trainer count held under greedy with §3 unmet.

- **Log #889–896 (A5, D's reads, search, and Evan's pause).** Research read C182's band at 44 as between, with survivors' Trainers holding where W's fall and arm 0 reading D − lists at −0.065 and −0.017, while frozen G3 gave the same decks +0.141 from the loop's edits and G2 barely moved (0-1 of 8 archetypes, staples recall 1 of 7). Under search D's top 12 at 29 fall on both seeds, from 0.507 and 0.575 to 0.351 and 0.366, against the lists' 0.505 and above W s49's 0.236 and 0.261, so the greedy level doesn't hold when both seats play better. C184's DR seeds were training from their Energy-heavy starts when Evan's pause came at 10:56:59, and they stopped after iterations 23 and 20 with checkpoints kept, the GPU clear of this project by 11:04.

- **Log #897–904 (A5, the pause: a design error found and the Trainer fall split).** Research found that D's and DR's Trainer hold was mostly the table's bonus raising Trainers' proposal mass, with selection neutral at best, so C182's G1, median, survivors and frozen G3's +0.141 fall as method reads while the start-deck effects, C185 and the search reads stand as reads of decks, and DR isn't resumed. CPU reads on samples split the fall: W's Trainer proposals drop because the out-choice comes to prefer Trainers (1.02, 1.04 to 1.31, 1.42 times their share of copies) with incoming mass flat, group moves carry about a quarter of it, and D's incoming decline is mostly the 4-copy cap, so it says little about the head. The mass-neutral bonus passes its CPU acceptance (Trainers within noise of no bonus at 8 starts, against the plain bonus's +0.46 to +1.00), and DN, neutral D, WR and C187's frozen head, H94's question that never ran, wait in held queues for Evan's resume.

**Recent (log #905–909).** Research holds any out-side arm until H0's read, so H0, DN, ND and WR will report Trainers' out share against their share of copies at each stage, and no run has data yet as Evan's pause holds. On W's whole saved populations the out-choice's preference reads between, leaning blunt: the table's top 12 rise to 1.26, 1.34 times their copies and the other 30 to 1.42, 1.49, a gap of +0.155 and +0.150 (SE 0.029, 0.038), so the head mostly cuts Trainers in general and aims a little on top. Both held queues died at about 15:17, around a failed restart attempt on the machine, and were relaunched at 16:43 with nothing lost, and the work through #909 went to `overnight-10-26` on Evan's push.

The full record is in [`notes/progress-log.md`](notes/progress-log.md).

**Next:**

1. On Evan's resume the held queues launch H0 s48, DN s50 and ND s48, then WR s50 and the seconds; `c184_read.py --accept` at iteration 4 is DN's live acceptance (proposed Trainers against WR's, within noise).
2. D's search at 44 and W at 29 under search, the pairing ahead of C186; then C186, the table fitted under search, after DN's first read.
3. The band reads: DN − WR at 44, neutral D against W, C187's proposed Trainers at 35-44, and `c187_read.py --mass` at each stage; an R-head at H0 brings an out-side arm.
4. As RAM allows: C181's step 1, W1 and W2's control (training held); C176's second table and W's beside read; M2 as a further judge in C185.
5. After those: full width on E2 bodies (not built); C175's seed 176; the engine's Third Eye and Buzzap dead prompt; C173's stage B2 not built; C171's B stays held, and if released it needs `--table-neutral` and a shape-neutral `name_weight` (#903).
6. Evan's rulings, only if still needed: practice decks selected on named draw copies (#726), concentrated tables in the drafts, and research's standing-rule question (#723, restated in #732); the Snorlax Thick Skinned marker suspect with the auditor, unmeasured and rare.
7. Scripted tests for the Muk / Dark Arbok and Alakazam items, if wanted; the `ar/` re-setup after the `rl/` and `env/` changes, and Evan's two standing decisions.
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
