# 2000s result #2: tournaments of 3, 6 and 9 deck-owning agents

> **Code.** The scripts this result ran (`rl/tournament.py`, `rl/league.py`, `rl/search.py`, …) were removed at log #65; they reproduce from the git tag `pre-simplify` (engine `3ee2238` for the runs, `c1cca1d` at the tag).

**Question.** If agents each own a network and a deck, start from different random decks, redraft
freely (up to 75% of the deck a round, with exploration) and play the decks they draft in a repeating
tournament, what changes with the number of agents? And does anything like the human metagame of the
July 2000 Super Trainer Showdown come back?

**Answer, in short.**

- **No convergence at any N.** Every agent keeps its own deck type for all 20 rounds. That is also what
  this drafting operator does by default, so it is not evidence that the tournament prevents collapse.
- **The equilibrium stays small (1–2 decks on average) as N grows**, so its share of the field falls.
  The meta is mostly transitive, and no effect of N on its structure survives the seed-to-seed spread.
- **None of the human metagame came back.**
  - 0 of 8 archived archetypes reached 50% card overlap.
  - The final equilibria play 0–2 of the 7 field staples, no more than the random starting decks.
  - Under one common pilot, the discovered decks win 20% against the 24 archived lists.
  - The one human-like signal is the choice of Basic Pokémon, which shifts strongly toward the
    field's.
- **Every run drifts the same way within two rounds**, to Pokémon-heavy, Trainer-poor, Energy-heavy
  piles full of unplayable evolutions. A large part of that comes from how the drafting proposes cards
  (225 of the pool's 277 card ids are Pokémon). The rest comes from pilots that do not use Trainers
  well.

The numbers below come from four runs. Each claim was recomputed by an independent checker, and its
strength rating is the checker's (`data/verified_claims.json`).

## Setup

`rl/tournament.py` (logs #59–62). N agents, each with a network and an optimizer of its own: copies of
pilot-v2 it349, the token model with d 256, 4 layers and 8 heads. Each starts from a different random
rules-only deck over the full 277-card pool. Every round has three steps:

1. **Tournament.** Every pair plays 32 greedy games, each agent piloting its own deck. Standings, the
   Nash equilibrium and cyclic triads are logged.
2. **Draft.** Every agent redrafts at once against the field, the other agents' decks from the start
   of the round.
   - Each agent has 90 value calls in climbs of at most 15 steps. A round may change up to 45 cards.
   - Exploration in card picks:
     - half of the added cards are drawn toward cards played least (weight floored at 0.25);
     - half of the climbs start from a random kick;
     - steps are drawn from softmax(value / 0.03);
     - one finalist is drawn at random.
   - Adoption is a two-stage real-game test: the best finalist on at least 96 games, then a re-test
     against the current deck on fresh games. It must win by 2 points, or, with probability 0.25,
     come within 3 points (an exploratory adoption).
3. **Training.** Each agent plays 8 PPO iterations on its own deck against the others and learns only
   from its own side.
   - Exactly 8,000 transitions per agent per iteration, collected with per-agent quotas.
   - Exploration in actions: an entropy controller holds each policy near entropy 0.75.

Nothing human enters training. The archived lists and SimpleBot are used only for evaluation.

| Run | N | Seed | Notes |
|---|---|---|---|
| tourn-3 | 3 | 1 | starting decks = the first 3 of tourn-6 and tourn-9 |
| tourn-3-s2 | 3 | 2 | the seed-to-seed spread |
| tourn-6 | 6 | 1 | |
| tourn-9 | 9 | 1 | |

Each run lasted 20 rounds. They took 1.5, 3, 5 and 1.5 hours.

## What changes with N

| | N=3 s1 | N=3 s2 | N=6 | N=9 |
|---|---|---|---|---|
| Equilibrium support, mean decks | 1.38 | 1.00 | 2.10 | 1.76 |
| as a share of N | 0.46 | 0.33 | 0.35 | 0.20 |
| Rounds with no pure equilibrium (of 21) | 4 | 0 | 12 | 6 |
| Cyclic share of triads | 0.19 | 0.00 | 0.10 | 0.05 |
| Deck types (20+ cards apart), every round | 3/3 | 3/3 | 6/6 | 9/9 |
| Closest pair of decks, final (cards) | 50 | 36 | 38 | 36 |
| Adoptions per agent-round | 0.42 | 0.42 | 0.45 | 0.44 |
| Exploratory adoptions | 1 | – | 10 | 4 |
| Own deck vs SimpleBot, run mean, round 19 | 0.88 | 0.81 | 0.77 | 0.72 |

Checked claims:

- **Equilibrium (suggestive).** Support stays small at every N. Round by round it is pure or a 3-deck
  mix, so its share of the field falls, though more slowly than 1/N (about N^-0.54). The N=6 share sits
  inside the N=3 seed range.
  - Mixing is genuine only at N=6. It is transient (rounds 0–10, p ≈ 0.001–0.003 for intransitivity)
    and driven mostly by one recurring cycle (a0 > a3 > a5 > a0).
  - At N=9 three apparent mixed rounds were solver artifacts: exact ties with an unbeaten agent.
  - The meta is mostly transitive: 85–86% of pairs at N=6 and N=9 agree with the standings order,
    against 68–73% for a structureless matrix.
- **No N effect on dispersion or transitivity (solid, low power).** Standings spread and
  Bradley-Terry scale, with noise removed, put N=6 and N=9 between or at the two N=3 seeds.
- **Adoption (suggestive).** No N effect on adoption rate or on cards per adoption. Most change happens
  in rounds 0–4. After that the rate is about 0.2–0.45 with 3–9 cards per adoption. Much of the
  adoption is noise: a re-test differs by about 6 points SD against a 2-point margin.
- **Play against SimpleBot on one's own deck.** It falls with N (0.88 / 0.81 / 0.77 / 0.72), but that
  is not significant across 4 runs (slope p ≈ 0.11). It also does not predict cross-play strength at
  all: r = −0.06 over the 21 agents, although the measure itself is reliable. **It is not a useful
  strength yardstick here.**
- **Exploration in play (solid).** In the second half of every run the controller held each agent's
  entropy at 0.74–0.77. The coefficient rose above its floor once entropy fell below target, after 13–70
  iterations.
- **The ≥70% drafting goal.** Counting non-Energy cards, 18 of 21 final decks are at least 70% drafted
  and 7 are fully drafted. Counting all cards, 4 of 21 are, because agents keep their starting basic
  Energy (76% of the cards kept from the start).

**Confound.** The training budget per agent is fixed, so data per opponent falls with N: 640k, 256k and
160k transitions per opponent at N = 3, 6 and 9. Draft deals and confirmation games per opponent fall
too. An N effect cannot be separated from per-opponent specialization without scaling the budget with
N − 1. N=6 and N=9 also have one seed each.

## Strength across runs (cross-play of the 21 final agents)

There are two round-robins (`data/tournament_crossplay.json`): each deck piloted by its own agent, and
every deck piloted by pilot-v2.

| Run | Own pilot, vs other runs | Common pilot (deck alone), vs other runs |
|---|---|---|
| N=3 s1 | 0.461 | 0.573 |
| N=3 s2 | 0.591 | 0.591 |
| N=6 | 0.431 | 0.428 |
| N=9 | 0.532 | 0.478 |

- **Deck over pilot (solid).** The deck explains about 70% of an agent's cross-play strength, the pilot
  about 30%. The pilot effect is real but comes mostly from a few agents (gain from −0.22 to +0.22).
- **Within-run standings track cross-play strength (solid)** (demeaned r = 0.86). The tournaments rank
  their own agents correctly.
- **N=3 decks are stronger under the common pilot (suggestive).** 0.57–0.59 against 0.43–0.48, and each
  N=3 run beats each N≥6 run head to head (0.57–0.62). The evidence is weak (p ≈ 0.06 one-sided by
  deck; at least 1/6 by run) and confounded by per-opponent exposure.
- **The strongest strategy is tourn-3-s2/a0** (0.78 own, 0.73 common). It is the pure equilibrium of
  both matrices in point estimate, but that purity is not robust at 32 games per pair.

## Recovery of the human metagame

| | N=3 s1 | N=3 s2 | N=6 | N=9 |
|---|---|---|---|---|
| Field staples played by the final equilibrium (of 7) | 0 | 0 | 2 | 2 |
| Archetypes rediscovered (≥50% overlap, of 8) | 0 | 0 | 0 | 0 |
| Best overlap any deck ever reached | 0.33 | 0.43 | 0.38 | 0.38 |
| vs the 24 archived lists, common pilot | 0.20 | 0.25 | 0.17 | 0.20 |

The 7 field staples are the cards in at least 75% of the archived lists: Professor Oak, Computer
Search, Double Colorless Energy, Gust of Wind, Scyther, PlusPower and Item Finder.

- **Random starting decks already play 0–2 staples and overlap 0.27–0.35.** Shared basic Energy
  inflates overlap. So drafting did not move toward the human lists.
- **Staple counts stay flat at the run level.** Most staple copies in the final decks were drafted in,
  though: 44 of 60, mostly Scyther, Double Colorless Energy and Oak.
- **The human field is much stronger.** Under one pilot (`data/tournament_vs_archived.json`) the 21
  discovered decks win 20% against the archived lists; the best wins 41.5%.
- **The one human-like signal (solid): field Basic Pokémon.** Among the Pokémon the agents chose, the
  share that are field cards rose from 0.04–0.11 at round 0 to 0.27–0.39 at round 20. The base rate is
  0.09, and all 21 final decks are above it. Among Basic Pokémon the share went from 0.08–0.23 to
  0.43–0.56. Ditto, Lapras and Gastly lead.

## What the decks became

- **Composition converged even though card lists did not (solid).**
  - The final mean over 21 decks is 29.0 Pokémon / 5.3 Trainers / 24.1 basic Energy / 1.5 special
    Energy. The archived lists average 13.9 / 27.5 / 14.6 / 4.0.
  - By round 2, 17 of 21 decks had more Pokémon than any human list and fewer Trainers than any; by
    round 20, 19 of 21.
- **The decks are unstructured piles (solid).**
  - 31.6% of Pokémon copies are evolutions whose pre-evolution is not in the deck, so they can never be
    played. Only 9.2% are evolutions with their line present, no better than the random starts (9.8%).
  - There is 1 complete Stage 2 line in 21 decks.
  - The drafter keeps adding orphans: 180 of the 193 orphan copies in the final decks were not in the
    starting deck.
- **Part of the drift is the proposal operator.** A swap adds a card drawn over card ids, and 225 of the
  277 ids are Pokémon. So random legal swaps alone push toward Pokémon. The value climb and the
  real-game test accept these swaps because the pilots get little from Trainers, the bottleneck seen
  since logs #32–36.
- **Bad starts can trap an agent.** In 2 of 4 runs an agent was last almost every round. tourn-9/a8
  started at 1 Energy / 7 Pokémon / 48 Trainers and became a Pokémon pile still short of Energy. It is
  the worst of all 21 in cross-play, although it plays its own deck well against SimpleBot. Its value
  head has only ever seen hopeless games, so it cannot steer the climb anywhere better.
- **Lineages keep their starting colour.** The same starting deck in different runs ends about 35 cards
  apart, against 53 for different starts. About 80% of the extra overlap is basic Energy kept from the
  start.

## Validity

- **Budgets and errors.** Every agent-iteration trained on exactly 8,000 transitions, and there were 0
  errors in training, tournaments and cross-play.
- **Noise.** One matrix entry at 32 games per pair has about ±0.09 SD, slightly above binomial in a
  replay (1.2x). A change between rounds needs to exceed about 0.25 to be read.
- **Capped games.** 0.16–0.26% of training games ran to the step cap, rising about 3x over the 20
  rounds. The analysis found one more card with an unset once-per-turn marker, Venomoth JU's Shift, in
  one N=6 deck. It is fixed in the engine since these runs (fork `c1cca1d`, with a spec).
- **Free cycles found and fixed during this experiment.** These are why tourn-3 was relaunched twice
  (the earlier attempts are kept as `runs/tourn-3-prefix` and `runs/tourn-3-loopbug`):
  - Tentacool FO's confirm "no" (log #58).
  - Dark Dragonair TR's Evolutionary Light, whose shuffle hid the repeat (log #62).
  - The env's per-turn cap of 250 decisions now ends a turn caught in any cycle the no-op tests miss.
- **Human prior.** pilot-v2's weights were trained on random decks drawn from the archived field's
  cards. That may favour field Pokémon, and it is a caveat on the one human-like signal above.

## What it points to

1. **The drafting operator, before the population.** Propose cards by class, not by id, and add or
   remove whole evolution lines. Measure dead cards from the agent's own games (cards it never plays)
   rather than with a game-specific rule. Or replace the climb with a draft policy trained on real
   results.
2. **The pilot's use of Trainers,** still the limit on any human-like deck.
3. **For the scaling question:** more seeds at N = 6 and 9, a budget scaled with N − 1, and restarts or
   borrowing from the field for agents stuck at the bottom.

## Reproduce

```sh
sh results/2000s-result-2/tournament_runs3.sh      # quota smoke test, then N=3, 6, 9 and N=3 seed 2 (~11 h)
PYTHONPATH=. .venv/Scripts/python notes/scripts/tournament_report.py runs/tourn-3 runs/tourn-3-s2 runs/tourn-6 runs/tourn-9
PYTHONPATH=. .venv/Scripts/python notes/scripts/tournament_crossplay.py --runs runs/tourn-3 runs/tourn-3-s2 runs/tourn-6 runs/tourn-9 \
    --common runs/pilot-v2/model_it00349.pt
```

`data/`:
- each run's per-round log and config;
- the run summary (`tournament_report.json`);
- the cross-play (`tournament_crossplay.json`);
- the discovered decks against the archived lists (`tournament_vs_archived.json`);
- the 40 checked claims with their corrections (`verified_claims.json`).

The networks are in `runs/tourn-*/checkpoint.pt` and `pilots_r*.pt`. They are not committed: N × 15 MB
per checkpoint.
