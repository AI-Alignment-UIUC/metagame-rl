# 2000s result #1: scoring decks by the pilot's value builds the best metagame

*2026-10-06 · Phase A (July 2000 Super Trainer Showdown, California) · plan item A5.2 · progress
log [#33](../../notes/progress-log.md) (the pilot) and [#34](../../notes/progress-log.md) (this run),
corrected in #35 · commits `2e5a6c1`, `d34e9fa`*

**Question.** Log #27 left three ways to judge a candidate deck inside the PSRO deck builder:
play real games with it, ask a learned matchup model, or read the play network's own value at the
start of the game. Which builds the best metagame from random decks, given the same time?

**Answer, from one seed.** The pilot's value. Starting from the same 16 random decks, its final
deck is even with the archived human field (50.3%). It beats the mixtures the other two designs
built 76.5% and 74.3%, and it is the hardest to exploit. It is a Haymaker 77% card-for-card like
Chris Graham's 6th-place 10-and-under list, with Double Colorless Energy, Computer Search and Bill
back in the deck. Real-game scoring is accurate but explores too little in the same time. The
matchup model is exploited by the search.

## Setup

| | |
|---|---|
| Card pool | The 56 cards the archived field played (`--pool field`) |
| Start | The same 16 random legal decks for every method (`--init cold:16 --seed 3`) |
| Pilot | Token + pointer policy fine-tuned 15 iterations with deck-out wins paying 0 (`pilot/model_it00014.pt`; log #33), greedy |
| PSRO | 8 iterations; up to 4 new decks per iteration; 48 games per pair; Nash over the real-game matrix |
| Search | `rl/search.py`, the same for all three: restarts from a random deck or a support deck (kicked 10 swaps away), a 12-60 card edit budget per search, single-card swaps, new decks ≥ 10 cards from every deck |
| Budget | 120 s of search per iteration for every method (wall clock, scoring included) |
| Machine | Capped at ~80%: GPU memory ≤ 80%, ≤ 16 of 20 threads (`rl/limits.py`) |

The three scorers:

- **games (a):** real games against the top 6 support decks, weighted by the Nash mixture, 24
  per pair. Every candidate in a step plays the same deals.
- **model (b):** an ensemble of 5 matchup models (`rl/matchup.py`), each refit on resampled
  results, ranked by mean + 1.0 × spread (optimism).
- **value (c):** the pilot's value at its first decision of the game against each support deck,
  averaged over 8 deals and weighted by the mixture. These are forward passes only, no games.

For **model** and **value**, the search stops at 90% of the budget. The 8 best distinct finalists
then play real games against the support, and the best go in (A5.2 step 3). Whatever the scorer,
every number in a matrix is from real games.

## Results

**The panel.** Each run's final Nash support (games 5 decks, model 3, value 1) and the 24
archived lists, all against all, 60 games per pair under the same pilot (31,680 games, 0 errors).

| | (a) games | (b) model | (c) value |
|---|---|---|---|
| Final mixture vs the archived field | 37.9% | 26.5% | **50.3%** |
| vs (a) games | — | 59.1% | **76.5%** |
| vs (b) model | 40.9% | — | **74.3%** |
| vs (c) value | 23.5% | 25.7% | — |
| Best panel deck against it (exploitability) | 84.9% | 86.7% | **71.7%** |
| Weight in the panel's Nash | 0.125 | 0 | 0 |

The archived lists keep 0.875 of the panel's Nash, so none of the three beats the human
metagame as a whole yet.

**The searches.**

| | (a) games | (b) model | (c) value |
|---|---|---|---|
| Wall time (matrix + search) | 19.2 min | 21.1 min | 19.0 min |
| Candidates scored | 1,404 | 8.6 million | 643,164 |
| Decks added (population) | 15 (31) | 32 (48) | 32 (48) |
| Mean error of the scorer's own estimate vs the real result | **0.081** | 0.587 | 0.268 |
| Proposals' real win rate vs the mixture they were built for | 40.5% | 23.6% | 35.5% |

- **games** is honest but slow. At ~1 candidate per second it finished one to three climbs per
  iteration, so it added 1-3 decks where the others added 4.
- **model** predicted 0.75-0.90 for decks that won 0-61%. Offline, the same model predicts
  held-out pairs well: on log #32's 64-deck matrix the error is 0.06-0.07, with 89-92% of
  winners right. Trained on 16 decks, though, it predicts new decks no better than a coin
  (error 0.25 against 0.26). A million candidates per iteration find exactly the decks it
  overrates, and confirmation games can only pick the least bad of a bad shortlist.
- **value** sits between them: a few hundred times the candidates of real games, overoptimistic
  by about 0.27, but pointed the right way.

## The deck it built

`value5-0`, the whole of run (c)'s final equilibrium, next to the closest archived list:

| Card | value5-0 | Graham (10-and-under #6) |
|---|---|---|
| Lightning Energy | 21 | 9 |
| Fighting Energy | 9 | 9 |
| Double Colorless Energy | 4 | 4 |
| Energy Removal | 4 | 4 |
| Hitmonchan | 4 | 3 |
| Scyther | 3 | 4 |
| Super Energy Removal | 3 | 4 |
| Electabuzz | 3 | 3 |
| Computer Search | 3 | 3 |
| Bill | 3 | 3 |
| Professor Oak | 2 | 3 |
| Machop | 1 | 0 |
| PlusPower | 0 | 3 |
| Gust of Wind | 0 | 2 |
| Scoop Up | 0 | 2 |
| Ditto | 0 | 2 |
| Energy Retrieval | 0 | 2 |

The engine is Graham's almost card for card. The differences are the Trainers the pilot
undervalues (PlusPower, Gust of Wind, Scoop Up, Energy Retrieval; logs #32-33). They are replaced
by 12 extra Lightning Energy, 34 Energy in all against Graham's 22. In the panel, the hardest
deck against it is Andrew Marshall's winning Haymaker (71.7%), which it overlaps only 45%.

The other two runs' top decks are further from any human list. Their labels are just the
nearest archived list's:

- **games2-0** (weight 0.32): 22 Psychic and Water Energy, 3 Mewtwo, 3 Lickitung, 4 Super
  Energy Removal and 3 Goop Gas Attack. Nearest is Marshall's Haymaker at 43%.
- **model6-0** (weight 0.50): 39 Energy, Hitmonchan, Chansey, Lickitung and Articuno. Nearest is
  Devin Diamond's Articuno / Hitmonchan / Scyther at 42%.

## What this does and doesn't show

- **One seed, 60 games per pair.** The gaps are large (head to head ±6% at 95% for 60 games per
  pair over this many pairs), but nothing is replicated yet.
- **The pilot shapes every answer.** It still values PlusPower, Item Finder and Gust of Wind
  below a basic Energy, so no builder can be expected to bring them back. Every scorer here
  judges decks through the same pilot.
- **Small pool.** The 56 field cards leak human card choice. The real claim is a cold start on
  the full Base-Rocket pool (A5.3).
- **Model under-tested.** The matchup model was run as designed, with optimism and confirmation
  but without the planned value feature. A trust region (candidates near measured decks) or the
  value as an input may rescue it, so it is not ruled out.

## Reproduce

From the repository root, with `runs/deckout-w0/model_it00014.pt` (or this folder's
`pilot/model_it00014.pt`, made by `pilot/deckout_test.sh`):

```sh
sh results/2000s-result-1/builders_compare.sh        # the three PSRO runs, ~60 min
PYTHONPATH=. .venv/Scripts/python notes/scripts/compare_builders.py \
    --runs runs/cmp-games,runs/cmp-model,runs/cmp-value \
    --policy runs/deckout-w0/model_it00014.pt --games 60 --json panel.json
```

## Files

| Path | What |
|---|---|
| `builders_compare.sh` | The three runs as launched |
| `panel.json` | The panel results above (also `notes/data/eval/builders_compare.json`) |
| `runs/{games,model,value}/log.jsonl` | Per-iteration PSRO log: support, proposals, predicted vs real, search statistics |
| `runs/{games,model,value}/population.json` | Every deck each run built, as card lists |
| `runs/{games,model,value}/matrix.npz` | Each run's real-game matrix (wins, games, names) |
| `pilot/model_it00014.pt` | The pilot checkpoint (1.6M parameters) |
| `pilot/deckout_test.sh` | How the pilot was made, with its control arm |
