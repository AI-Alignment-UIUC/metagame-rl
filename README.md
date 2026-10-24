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
*Updated 2026-10-23.*

**Where things stand.** A0, A1 and A3 are done, A2 has its ladder and the SimpleBot matchup matrix, and Phase B's engine plays two 2005 lists and passes a fuzz over 340 cards. Every learned drafting loop has ended in Chansey / Snorlax walls with more Energy and fewer Trainers than the human lists; draft and selection changes move their shape but never their type, and with the 2000 round rule in the game (Evan's decision) two seeds of the loop came closest to the human shape of any run (6.3-6.8 cards from the human medians against 9.6-11.7 untimed) while walls still held 44-69 of 99 decks. The cause sits in the judge: pilots grown with the walls rate them 0.68-0.75 against the human lists untimed and about half the event points under the rule (0.504), and the walls lose to the human field only when both seats search and the round is cut early, at a turn count no outside source documents. Human-free pilots still trail pilot-v2 on the human lists by 190-320 Elo untimed, though the loop's own pilot under the rule played them level with pilot-v2 under the same rule; paid the round's points a pilot plays for the lead at the cut rather than faster, and soft search targets read +55 and then −11 Elo over that at their first two looks. The method (`notes/method.md`) now runs unattended: a supervisor outside Claude starts short, fresh rounds and launches every run under the method's limits as code, which bar further forks of the 479 state until a prevention start, and it waits on Evan to install its scheduled task.

**Earlier work:**

- **Log #1–56 (A0–A5, B1–B2; rolled up from eight block summaries).** The engine and environment cover
  the 2000 field and were verified against an oracle (0 mismatches over 1.65M checked decisions), with
  engine faults and free action cycles fixed on the way, and Phase B moved to Worlds 2005, whose engine
  branch plays Birds and ZapTurnDos and passes a 1,500-game fuzz over 340 cards. Trained pilots beat
  SimpleBot (the token model 93% when trained on the archived decks, human-free pilot-v2 near 83%), but
  deck search driven by the pilot's value keeps flooding decks with Energy and no change to the search
  fixed it, neither extra attention nor play-time search transferred to an outside opponent, and the
  first built metagame to beat the archived field (60.7%, [2000s result #1](results/2000s-result-1/)
  and log #40) came from piloting every PSRO iteration. Under the general self-discovery scope set at
  #51, co-evolving the decks and one pilot over the full pool rediscovered Computer Search, Scyther,
  Oak, Energy Removal and Double Colorless Energy but collapsed to one deck type, so the metagame moved
  to a league of deck-owning agents with separate networks and a two-stage real-game adoption check.
- **Log #57–120 (A4, A5, plan; rolled up from eight block summaries).** Tournaments of deck-owning agents
  ([2000s result #2](results/2000s-result-2/)) kept their deck types distinct but drifted into Pokémon piles (0/8
  archetypes), so the meta level became one learned loop, `rl/metagame.py` (99 decks sharing one pilot and one draft head
  trained on game results, with turnover; the older code at the `pre-simplify` tag), whose first best decks broke even
  with the human lists under pilot-v2. Pilot architecture screens stayed within their noise, and taking the human lists as
  ground truth (Evan) traced the decks' distance from them to the pilot, which does not set up before attacking and so
  values every Trainer but Oak and Bill below an Energy; the lab (`rl/lab.py`) then trained the loop as a main line whose
  forks are decided against it on bars set by A/A cards, Evan's ideas first and then the approved three-stage plan. It
  adopted 2 PPO epochs, 6 swaps a draw, the result-only draft reward, Evan's deck-free board encoder, learning rate 2e-4
  and a slower draft head, but no pilot change (memory in three forms, expert iteration toward a turn search, in-turn
  credit, entropy, depth, slot binding) moved Trainer competence from 0.43–0.48, practice before a draw counts failed on
  deck shape, and the population held one deck type from 160 on while its shape swung (closest to the human lists at 360,
  10.5 Energy above them at 400 in a deck-out meta), so when the plan's stall rule fired Evan chose a league of three
  draft heads sharing one pilot; lab bookkeeping faults that silently changed or risked decisions recurred throughout and
  were each fixed as found.
- **Log #121–128 (A5).** The league's heads drafted Pokémon piles and then the main type, from random decks the recipe
  fell within 40 iterations into Pokémon piles that never attack, and by 440 the main type held 36.5 Energy; #127 traced
  the one deck type to a drafting ratchet (every deck moves each iteration to a draw of 6 forced changes whatever its
  results, so the collapsed head's favourite card piles up, and basic Energy, the one card without a copy limit, piles up
  through Energy-for-Energy null swaps) and to a pilot so specialised that no other type can win a place (the main decks
  beat the human lists 0.80 under it and 0.26 under pilot-v2), which is also why the league failed. Built against the two
  traps: selection of draws on real results, group changes, practice games and turnover from wide random decks, decks
  judged by greedy rather than sampled play, and screens that run such ideas in parallel outside the lab. A shutdown and
  a sleep of the machine (23:05 and 23:27) killed every run, the lab's cards included, and the screens were relaunched
  from 460.
- **Log #129–136 (A5).** In screens beside the lab from the main line at 460, greedy judging, selection alone, a cap on
  any one deck type (the shared draft head, its choice collapsed, drafted every new deck back into Chansey / Snorlax),
  pilot-v2 frozen as the only or a second judge, and the method from scratch with a discount all failed to move the decks
  toward the human types, while a new, uniform draft head with selection, an entropy floor and group changes brought the
  best decks from 36 to 8-14 cards off the human medians in three screens (a median of 28 Trainers for a while), inside
  the same type and swinging back as the head's choice narrowed. Head-to-heads on the human lists showed why the type does
  not change: every pilot grown in the population, one that practised the human lists for 20 iterations included, plays
  them 27-45 Elo worse than pilot-v2, its starting point, so it rates its own decks above the human lists (0.71-0.83)
  where pilot-v2 rates them far below (0.20-0.32), as the ground truth says. A KL anchor toward pilot-v2 on the practice
  games was built to keep the pilot general and runs against a matched control, two screens being what the machine holds
  after four ran it out of memory.
- **Log #137–144 (A5).** A varied population (turnover capped by type, every 5 iterations) kept the shared pilot general, and a KL anchor toward pilot-v2 made it about 65 Elo better on the human lists, yet the decks stayed Chansey / Snorlax walls: their verdict depends on who pilots them, every card they use is implemented as printed, and they win long games on prizes that one-turn search on the human side wins back, so the pilot's tactical play is the deficit. A significance gate on deck moves held the human shape (9.5 cards off over 490-499 against 15.7) but not the type, and Evan's turn limit for draws (40, 70, 120 turns), challenger practice and an exploiter league were screened or started from the 479 state. A literature review then read all of this as one failure, a shared pilot judging the decks it already plays well under global, noisy selection, and ranked search-strength judging, soft gated search targets and Monte Carlo value targets first, ahead of more diversity machinery.

- **Log #145–152 (A5).** Challenger practice, an exploiter league, Monte Carlo value targets and search judging under a min rule (inert: 6 selection changes against 15.5 from noise) all left the walls in place, every pilot grown in the population rates them 0.68-0.75 against the human lists (pilot-v2 0.26), and within the human field alone the trained pilots judge like the real field, so the judge's error is specific to the walls and long games. Scored exactly under the 2000 round rule, the greedy walls take 0.48-0.55 of the points at cuts of 20-40 turns and more at every later cut, one-turn search on both seats with a 50-60-turn draw puts them at 0.44-0.46, and searched play does not replay exactly on the same deals, so that leading result needs replicating. A ledger of 69 verified mechanism-level families (`notes/hypotheses.md`), research on 11 angles and an iterative method (`notes/method.md`, approved by Evan for now) turned the research loop's own collapse (25 of 27 screens forked from two wall states) into written rules for rival explanations, pre-written bands and an exploration floor, with a first-cycle plan of 16 items (`notes/plan-cycle1.md`) that puts cheap judge, input and noise-floor probes and a from-scratch warm-up first.

- **Log #153–160 (A5).** Two more seeds of the significance gate replicated its shape effect but not the type (walls fill 67-75 of 99 decks), and on all 24 human lists under the exact 2000 round rule the walls take under half the points only when both seats search and the round is cut early (break-even near turn 56 for the 479 walls, 45 for the Energy-heavy 460 walls, which greedy play rates highest), while search helps only the lists' seat. A pilot trained from random weights on rules-generated wide decks never learned the stall and matches pilot-v2 on such decks, but trained on to 119 it still plays the human lists 274 Elo worse after a 175-Elo gain and rates the walls 0.52-0.57, because four in five of its practice games end by benching out rather than in a Prize race. Both lines point at the same missing pieces: where the round ends, a stronger player of human-like decks, and practice games that look like theirs; twice in the day finished runs sat unread for hours.

- **Log #161–168 (A5).** Evan approved the 2000 round rule for training and judging and the cost of GPU search, so the rule became an opt-in part of the game (an unfinished game goes to the side with more Prizes taken, scored 3 / 2 / 1 / 0); outside research confirmed the 20-minute round and its procedure but not how many turns it allowed, leaving the cut a per-game draw from 20-45 turns, and found that 2000 players finished Prize races in about 13-14 engine turns against our pilots' 34-41. Paid the event's points, the from-scratch pilot became 54 Elo better on the human lists under the rule but 65 worse untimed, playing for a Prize lead at the cut rather than finishing faster, while the plain pilot barely improved and rated the walls ever higher; a learned practice curriculum (replay by the pilot's positive value loss, with card edits) moved practice from bench-outs to Prize races and its median deck to 13 / 28 / 17 in five iterations, but untimed its longer games ended by deck-out and the stall rule stopped it. The loop under the rule ended closest to the human shape of any run (distance 6.3 against 9.6-11.7 for the same recipe) with walls still 47-69 of 99 decks, and GPU-served search replays greedy exactly at one candidate and runs 2.7 times the CPU path's games a second, still too slow to search every judged game; finished runs sat unread for up to 50 minutes at a time.

- **Log #169–176 (A5).** Under the round rule the learned curriculum's score turned practice into bench-outs, because a win on time pays a third of a finished one, while the pilot the loop grew under the rule from the 479 state played the human lists level with pilot-v2 under the rule and, as a judge, gave the walls about half the event points (0.504, against 0.67 untimed), yet the loop's own decks stayed mostly walls. A second seed of the loop under the rule replicated its shape (6.8 cards from the human medians against 9.6-11.7 untimed) but not its fewer walls (44-53 of 99 against the first seed's rise to 69), and soft search targets for the pilot read +55 Elo over the clocked pilot at their first look and −11 at the second, two such trainers running the 31 GB machine down to 4 GB free. The research loop was then made unattended: a supervisor outside Claude starts short, fresh rounds on events and launches every run under the method's limits as code, which at once bars further forks of the 479 state (every one of the last 12 screens) until a prevention start, and its dry round found two results left unlogged and runs that had all ended together at 03:03.

**Recent (log #177).** The loop was started unattended on Evan's go-ahead, its rounds on his Claude plan rather than an API key and told in his words to keep to the ground truth, stay out of local minima and spend the night on GPU runs. Every round now opens on a table of each screen's best decks against the human medians, which puts the two round-rule seeds 3.2-5.2 cards off them (about 2-3 Energy over) and the gated recipe untimed 13.7 off (7 Energy over, 6 Trainers short).

The full record is in [`notes/progress-log.md`](notes/progress-log.md).

**Next:**

1. The unattended loop's first night (task `metagame-loop`): read each round's handoff and `runs/loop/rounds.jsonl`.
2. Log debt (first round, from `runs/loop/dry-plan.md`, re-checked): C47 seed 6's final-pilot verdicts; the 03:03 ends of
   C49 at iteration 184 and of C47 seed 7's waiter.
3. C49 resumed through `loop.py launch` to its 179 and 199 looks (soft search targets against the clocked pilot); then
   C49b from 129, one probing trainer at a time.
4. A prevention-start screen, with candidates from a fresh lean-lead (the floor bars more 479 forks); C47 seed 7 under
   Evan's row 41 once its chain passes `--turnover-every` once.
5. The curriculum's score normalised per outcome scale (C48); C03's gross check, then searched judging under the rule.
6. C09 and C07 on the GPU lane; the rest of the C33 + C40 message (engine fixes, the Stage 3 bootstrap).
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
