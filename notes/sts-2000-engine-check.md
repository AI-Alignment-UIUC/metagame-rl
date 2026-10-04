# Can ryuu-play run the July 2000 STS metagame? — verification, 2026-10-03

> **Status: the gap is closed.** The three missing cards were implemented the same day; see
> §7. The working fork is the `ryuu-play/` submodule, branch `sts-2000-pool`, commit `f16e2ea`.
> **All 24 archived STS California decklists now build and start a real game.**

Checks the proposal to move the ground-truth target from Worlds 2013–14 (see
`tcg-rl-research-notes.md` §5) to the **2000 Super Trainer Showdown**, on the claim that the
format is fully implemented in ryuu-play apart from a 3-card gap and has a real recorded field.

Everything below was measured this session against ryuu-play `9cd20b6` (2026-06-18, shallow
clone) on Node v24.14.1, 20 cores. The event data is the Sep-8 scrape in
`notes/data/2000-super-trainer-showdown-*/`, re-scraped independently today and byte-identical
on deck count, card count and the two transcription corrections.

## Verdict

**The California claim holds, almost exactly as stated. The New Jersey claim does not.**

- STS California 2000 is a 24-deck field over **56 distinct cards**, and **53 of them are
  implemented and registered** in ryuu-play today.
- The gap is **exactly the three cards named**: Ditto, promo Mewtwo, promo Mew — and one of the
  three is a one-line change, not an implementation.
- STS New Jersey 2000 is **not** a usable second data point. It is a Gym-legal November format;
  it needs 19 Gym Heroes / Gym Challenge cards that ryuu-play does not have at all, and
  **0 of 24** lists are buildable.

## 1. California: the whole gap

`node notes/scripts/ryuu_pool_coverage.js <ryuu-play>`

| card | copies | decks | status |
|---|---|---|---|
| Mewtwo (Movie Promo) | 27 | 8/24 | different printing — only Base Set Mewtwo exists |
| Ditto (Fossil) | 22 | 11/24 | **card file exists, commented out of the set index** |
| Mew (promo) | 1 | 1/24 | no card file |

Buildable verbatim, cumulatively:

| after | decks |
|---|---|
| today | 7/24 |
| re-enable Ditto | 16/24 |
| + promo Mewtwo | 23/24 |
| + promo Mew | **24/24** |

### Ditto is not missing, it is switched off

`packages/sets/src/base-sets/set-fossil/index.ts` has its import and its `new Ditto()` entry
commented out — the only disabled card in all four base-era sets. The file itself is a 198-line
implementation of Transform: it copies HP, type, weakness, resistance, retreat and attacks, and
treats attached Energy as any type. Two `TODO`s remain: copying **passive** Pokémon Powers, and
the `enableAbility` flag on the copy prompt. In this pool that leaves Ditto-copying-Mr. Mime
(Invisible Wall) and Ditto-copying-Muk (Toxic Gas) wrong; both appear in the field, so the
TODOs need closing, not just the comment removing.

### The two promos (exact text, from pokemon-tcg-data `basep`)

- **Mewtwo, WBSP #3** (reprinted #14) — Basic Psychic, 70 HP, weak Psychic ×2, retreat 2.
  *Energy Absorption* [P]: attach up to 2 Energy from your discard pile to Mewtwo.
  *Psyburn* [P][P][C] 40. Both are **attacks**, not a Power — straightforward to add.
- **Mew, WBSP #8/#9** (identical text) — Basic Psychic, 50 HP, weak Psychic ×2, retreat 1.
  *Psywave* [P] 10× per Energy on the Defending Pokémon. *Devolution Beam* [P][P]: return the
  top Evolution card to its owner's hand and clear its conditions. The devolve machinery already
  exists for Base Set Devolution Spray, so this is mostly reuse.

Note ryuu-play has **no promo set folder at all**, so these two need a new set alongside the
existing four, not just two files.

## 2. The implemented cards are implemented correctly

Two independent checks, both run today.

**Card data**, `ryuu_card_data_check.py` against PokemonTCG/pokemon-tcg-data:
263 card files, 212 Pokémon compared, **1908 field checks** (hp, type, stage, evolvesFrom,
weakness, resistance, retreat, attacks, powers) → **1 mismatch**, and it is cosmetic
(BS Raticate Super Fang damage `''` vs `'?'`).

**Behaviour**, `ryuu_rulings_tests.js` against dated 2000-era Compendium rulings:
**22/23 pass**. The one failure, T18, offers Mysterious Fossil as a starting Basic instead of
forcing a mulligan — a real engine bug, but **Mysterious Fossil appears in zero California
lists**, so it does not touch this field. (It does appear at New Jersey.)

Caveat worth carrying: base-era cards have **2 spec files** in `packages/sets/tests/base-sets/`
(both Jungle) versus 116 for the ex-sets. The data is verified and the 23 rulings are verified;
the rest of the base-era behaviour is unexercised. "Engine bugs become meta bugs" still applies.

## 3. Throughput — first numbers (the §7 open item)

Single-threaded, Base-era 60-card decks, `ryuu_throughput.js`:

| | |
|---|---|
| game setup to a stable state | 0.65 ms → ~1,500 games/s |
| `Simulator.clone()` | **0.033 ms → ~30,000 clones/s** |
| `PassTurnAction` dispatch + reduce + prompt resolution | 0.551 ms → ~1,800 dispatches/s |

A pass-only game to deck-out ran 94 turns in ~52 ms.

> **Correction.** An earlier draft of this section read "the deep-clone fear in the research
> notes is unfounded — clone is ~6% of a dispatch". That was wrong, and §8 shows why. The 33 µs
> figure came from cloning a *freshly set up* state, and it was compared against a dispatch that
> already contains a clone of its own. Measured properly, `deepClone` is **55% of engine time**,
> and a late-game clone costs 13× a setup-time one. The original concern in
> `tcg-rl-research-notes.md` — "deep-clone per dispatch may dominate" — was correct.

### 3b. Real bot-vs-bot games (`ryuu_selfplay.js`)

ryuu-play only drives SimpleBot through its websocket server — `BotGameHandler` reacts to
`onStateChange` and dispatches through a `Game`/`Client` pair. `ryuu_selfplay.js` runs the same
`BotAi` against a bare `Simulator` instead, which is what an RL harness needs. Archived STS
decklists, random flips and shuffles, single core:

| | |
|---|---|
| actions per game | 135 |
| median turns | ~46–55 |
| whole game, SimpleBot both sides | **1.8 s → 0.6 games/s/core** |
| &nbsp;&nbsp;of which policy | 94–95% |
| &nbsp;&nbsp;of which engine | 5–6%, **~0.8 ms/action → ~110 ms/game** |
| engine-only ceiling (policy with no search) | **~9 games/s/core** |

**The engine is not the bottleneck — SimpleBot is.** It searches one ply by deep-cloning the
state and dispatching every candidate action, so it costs ~30× the engine per real move. The
earlier ~10 games/s/core extrapolation was right; what it missed is that a *baseline opponent*
costs far more than the simulator.

What this means for the plan:

- A trained network replaces that search, so the budget to design against is **~9 games/s/core**,
  not 0.6 — and that figure does fan out across cores (§3d: ~55–65 real games/s on this box).
- SimpleBot is unusable as a bulk self-play opponent at 0.6 games/s/core. It is still fine as the
  *floor* in evaluation (§5 of the research notes), where hundreds of games suffice, not millions.

Games end plausibly, which is the check that the bots are really playing rather than stalling:
over a sample, **50% on prizes, 25% bench-out, 25% deck-out**. A quarter decking out and a median
near 50 turns is weak play for a Haymaker format — expected from SimpleBot, and exactly the
"discovered meta reflects the agent's skill ceiling" coupling the research notes flag.

### 3c. Seat bias — no evidence of one

`ryuu_selfplay.js --mirror` plays every archived deck against **itself**, so deck strength
cannot confound the result and anything away from 50% is seat or policy bias. Over
**288 mirror games** (24 decks x 12): **seat A 54.5% ± 5.8** (95% CI 48.7–60.3), so the
first-player edge is **not distinguishable from zero** at this sample size.

This is worth having because the uncontrolled runs point the other way: rotating pairings gave
seat A 40% (n=40) and 43% (n=160). Those were deck strength, not seat — which is the whole
reason the research notes call for swapped seats in human evaluation. Same control, applied to
the bot baseline.

Per-deck mirror results spread 3/12 to 11/12. With 12 games the standard error is ~1.7 wins, so
a couple of 2σ-looking decks across 24 is what chance produces; none of it is signal yet.

### 3d. Scaling across cores

Games share no state, so this should be embarrassingly parallel. It is not, with SimpleBot in
the loop. 20 games per worker on a 20-core box (`--workers N`):

| workers | games/s | speedup | s/game per worker |
|---|---|---|---|
| 1 | 0.67 | 1.0× | 1.35 |
| 4 | 1.34 | 2.0× | 2.84 |
| 8 | 3.00 | 4.5× | 2.52 |
| 16 | 3.49 | **5.2×** | 4.43 |

Each worker gets *slower* as more run, which is the signature of allocation pressure rather
than CPU saturation — SimpleBot deep-clones the whole game state once per candidate action.

`--nopolicy` isolates that: it keeps SimpleBot's prompt resolvers but drops every tactic, so
the bot falls straight through to PassTurn and nothing searches. Single core, pass-only games:
**16.7 games/s, 622 µs/action, 96 actions/game** (all deck-outs, as a pass-only game must be).
Scaling that to a realistic action mix — 135 actions at the ~850 µs real games cost — gives
**~9 games/s/core**, which is exactly what the in-game engine timer reported. Two independent
routes to the same number.

Run the same sweep with `--nopolicy` and the picture inverts — 400 games per worker:

| workers | games/s | speedup | efficiency |
|---|---|---|---|
| 1 | 15.0 | 1.0× | — |
| 4 | 57.7 | 3.9× | 96% |
| 8 | 109.1 | **7.3×** | 91% |
| 16 | 126.3 | 8.4× | 53% |

**The engine parallelises fine.** Near-linear to 8 workers; the fall-off at 16 is what you
expect when 20 logical cores are ~10 physical plus hyperthreading. The poor scaling in the
table above is SimpleBot's allocation churn, not the simulator.

So the budget for a PSRO loop on this one box, engine-bound with a cheap policy, is
**~110 pass-only games/s at 8 workers**, or — correcting for a realistic action mix (135
actions vs 96, 850 µs vs 622 µs, so ~1.9× the work per game) — roughly **55–65 real
games/s**, about 200k–230k games/hour. That is a workable PSRO budget for a 56-card pool.

One more free validation: with no policy at all, seat A won 3168 of 6400 (**49.5%**). The
engine itself has no seat artifact, so whatever the mirror test's 54.5% is, it is not coming
from the simulator.

## 4. Why New Jersey is not the second data point

24 lists, 21 cards unavailable (19 of them Gym-set, plus Ditto and promo Mewtwo), **0/24
buildable**. The misses are Gym Heroes / Gym Challenge almost throughout — Rocket's Zapdos
(35 copies, 14 decks), Misty's Wrath, Erika's Dratini,
Brock's Sandshrew/Sandslash/Rhyhorn/Lickitung, Lt. Surge's Electabuzz, Rocket's
Scyther/Moltres/Hitmonchan, and the Stadiums (Chaos Gym, Narrow Gym, No Removal Gym, Pewter City
Gym) plus Secret Mission and The Rocket's Trap. Recovering it means implementing two whole sets.

This matters for the proposal: **the July 2000 format gives one 24-deck field, not two.** If a
second point is needed, the realistic options are a different 2000 event in the same Base–Rocket
legality, or accepting a single field and leaning on the three age divisions (the existing
`summary.json` already breaks the field down by division) as quasi-replicates.

## 5. What the field actually looks like

From `data/2000-super-trainer-showdown-california/summary.json`: 8 labelled archetypes,
Wigglytuff 10/24 (42%), Haymaker 7/24 (29%), HHI 0.274, effective archetypes 3.65. Top-2 share
71%. That is a concentrated meta — good for rediscovery as a *yes/no* ("does Wigglytuff appear in
the equilibrium support?") and weak for distribution matching, consistent with the standing note
that human metas are not equilibria.

## 6. Remaining work

1. ~~Un-comment Ditto, close its two TODOs~~ — done, §7.
2. ~~Add a promo set with Mewtwo WBSP #3 and Mew WBSP #8~~ — done, §7.
3. ~~Add the 24 lists as engine regression decks~~ — `ryuu_sts_decks_check.js`, 24/24.
4. ~~Write the headless bot-vs-bot harness and re-measure throughput with a real policy~~ —
   done, `ryuu_selfplay.js`, §3b. **The engine is not the bottleneck; the baseline bot is.**
5. Fix T18 (Mysterious Fossil mulligan) before anything touches New Jersey or Fossil-era decks.
   It does not affect the California field.
6. Now open: **fork-vs-port can be decided on §3b–3d.** ryuu-play sustains ~55–65 real
   games/s on one box with a cheap policy and parallelises near-linearly to 8 workers, so
   the engine is not the reason to port. Keep SimpleBot only as an evaluation floor; it costs
   ~30× the engine per move and will not scale as a bulk self-play opponent.

Unverified here: the separate claim that Base–Jungle gives "9 known-good archetypes" with zero
implementation work. Plausible but not checked against a source.

## 7. What was implemented (`ryuu-play/` submodule, branch `sts-2000-pool`, `f16e2ea`)

**Ditto FO** — re-registered in `set-fossil/index.ts`, and both TODOs closed.

- `enableAbility: { useWhenInPlay: true }` on the Transform prompt, so the copied Pokémon's
  in-play Powers are offered next to its attacks.
- Passive Powers are copied by standing the imitated card in Ditto's slot for the length of
  one `reduceEffect` call, which makes that card's own `cards.includes(this)` guards resolve
  the way "treat it as if it were the same card" requires.
- Two traps found while doing it, both now covered by tests:
  - **Double application.** Ditto always copies the *Defending* Pokémon, so that card is
    always in play and already receives every effect it recognises by attack or Power
    identity. Forwarding those as well applied them twice — Ditto copying Mewtwo BS's Psychic
    counted the defender's Energy twice and turned a 40 into a lethal 100. Delegation is now
    restricted to effects aimed at Ditto's own slot.
  - **Infinite recursion.** Transform asks the store whether its Power is blocked, and the
    store propagates that question back through Ditto. A guard makes a nested lookup report
    "not transformed".

**New `set-promos`** (Wizards Black Star Promos) with the two cards the field played.

- **Mewtwo PR #3.** Energy Absorption moves the Energy out of the discard pile directly
  rather than through `AttachEnergyEffect`, because Rainbow Energy's 10 damage and Full Heal
  Energy's heal both read *"when you attach this card from your hand"* and this is not that.
  Attaching through the normal effect would have silently done both. It also attaches to the
  Active Pokémon rather than to this card, so a Ditto copying Energy Absorption works —
  and the card polices its own slot, because `AttachEnergyPrompt.validate` does not.
- **Mew PR #8.** Psywave counts Energy *cards* (a Double Colorless is one). Devolution Beam
  returns the highest Stage to **its own player's** hand, clears that Pokémon's conditions,
  and does not heal it — so devolving a damaged Blastoise onto a 70 HP Wartortle knocks it out.

### Verification

| check | result |
|---|---|
| ryuu-play's own spec suite | **541 specs, 0 failures** (25 new) |
| STS card interaction suite (`ryuu_sts_cards_tests.js`) | **68/68** |
| 2000-era Compendium rulings (`ryuu_rulings_tests.js`) | 22/23 — the one failure is the pre-existing T18 |
| card data vs pokemon-tcg-data, promos included | 214 Pokémon, **1926 field checks, 1 cosmetic mismatch** |
| pool coverage | *every card in the California field is implemented and registered* |
| archived decklists built and started | **24/24** |
| throughput | 0.514 ms/dispatch — unchanged |
| eslint on the changed files | clean |

The interaction suite deliberately goes after the ways these cards could break each other:
Toxic Gas switching Transform off and back on, Invisible Wall on a transformed Ditto, Ditto
copying Ditto, Ditto copying Mewtwo PR and pulling from its *own* discard, special Energy
attached from the discard not firing its from-hand text, Devolution Beam through Dark
Vileplume, a devolution that causes a knockout, and a full game to deck-out with a Ditto
active to prove the delegation terminates.

One printing had to be assumed: Devin Diamond's 2 Machop are unannotated and Machop exists in
both Base Set and Team Rocket. Taken as Base Set — the archive annotates reprints and leaves
the original bare, and Base Set Machop (Low Kick 20 for one Energy) is the only sensible
include next to TR's Punch/Kick. `ryuu_sts_decks_check.js` prints the assumption.

## Repro

The working fork is the `ryuu-play/` submodule (branch `sts-2000-pool`). From scratch:

```
git clone https://github.com/keeshii/ryuu-play && cd ryuu-play
npm install --workspace=packages/common --workspace=packages/sets --workspace=packages/simple-bot
npm run compile -w packages/common && npm run compile -w packages/sets
(cd packages/sets && npx jasmine-ts "tests/**/*.spec.ts")   # the repo's own suite
```

Then, with `R=../ryuu-play` from `notes/scripts` (every script also reads `$RYUU_PLAY`):

```
node ryuu_pool_coverage.js   $R                 # which field cards are missing (sections 1, 4)
node ryuu_sts_cards_tests.js $R                 # Ditto / Mewtwo PR / Mew PR interactions (section 7)
node ryuu_sts_decks_check.js $R                 # build all 24 archived decklists (section 7)
node ryuu_rulings_tests.js   $R                 # 2000-era Compendium rulings (section 2)
node ryuu_throughput.js      $R                 # raw per-dispatch cost (section 3)
node ryuu_selfplay.js        $R --games 40      # real bot-vs-bot games (section 3b)
node ryuu_hotspots.js        $R                 # where engine time goes (section 8)
node ryuu_state_vector.js    $R                 # state vector analysis (section 9)
py   ryuu_card_data_check.py --ryuu $R --sets BS:base1,JU:base2,FO:base3,TR:base5,PR:basep
```

For a function-level profile:

```
node --cpu-prof --cpu-prof-dir=. ryuu_selfplay.js $R --nopolicy --games 150
node cpuprofile_top.mjs CPU.*.cpuprofile
```

`ryuu_selfplay.js` also takes `--mirror` (seat bias with the deck held fixed), `--matrix`
(archetype matchup table), `--workers N` (fan out across cores), `--deck`/`--vs` (one pairing),
`--list`, and `--seeded` (deterministic, so games repeat exactly).

Two shared modules sit underneath: `ryuu_harness.js` registers the format once and exposes the
board-rigging and prompt-resolution helpers the test scripts use, and `ryuu_sts_decks.js` turns
an archived `cards.csv` into ryuu-play card lists (printing resolution included).

## 8. Where the engine's time actually goes

`node --cpu-prof` over 150 engine-only games, self time:

| | share | what it is |
|---|---|---|
| `deepClone` + its inner closure | **55.5%** | `utils.js` |
| `propagateEffect` + its two closures | **30.5%** | `store.js` |
| `reduceEffect` dispatch | 2.5% | |
| all 233 card implementations combined | **<2%** | |

The card code is noise. Everything costs is in two places in the core.

### 8a. The whole state is deep-cloned on every dispatch, and it grows

`Store.reduce` opens with `deepClone(state, [Card])` as a rollback backup in case the action
turns out to be illegal. Cards are excluded, so it copies only the structural objects — but it
does this for **every** dispatched action.

Worse, the cost is not constant. Measured over one game:

| actions in | prompts | logs | objects cloned | clone cost |
|---|---|---|---|---|
| 0 | 4 | 0 | 194 | 60 µs |
| 40 | 5 | 116 | 429 | 189 µs |
| 96 | 5 | 286 | 769 | **764 µs** |

Resolved prompts *are* pruned (prompts stays at ~5). **`state.logs` is not** — it accumulates
one entry per game event and is deep-cloned on every subsequent dispatch. Clone cost grows
**12.8× over a single game**, which makes a game O(n²) in its own length.

Clearing `state.logs` each action, changing nothing else: **20 -> 32-45 games/s, a 1.65-2.2x
speedup** across repeated runs. Logs are pure debug output for an RL harness.

### 8b. Every card in the game is asked about every effect

`propagateEffect` collects every card from both players' stadium, supporter, active, bench,
prizes, hand, deck and discard into one array, **sorts it**, then calls `reduceEffect` on each.
Measured:

- **17.3 effects per action**, each propagating over **120 cards**
- **2,076 `card.reduceEffect` calls per action — ~200,000 per game**
- only **40 of the 60** distinct cards in a deck even override `reduceEffect`; the rest are
  asked 2,076 times an action to do nothing

The sort is re-done on every one of those 17.3 effects: **8.4 µs × 17.3 = 145 µs/action, ~27%
of the total**. `localeCompare` is not the culprit — a plain `<`/`>` comparator measured
*slower*. The cost is building and sorting a 120-element array at all. And the result is
invariant: cards move between zones but the set of 120 never changes within a game, so the
sorted order could be computed once.

### 8c. What that is worth

Both changes applied as a scratch experiment (logs excluded from the backup clone; propagation
order cached), then reverted:

| | µs/action | games/s/core |
|---|---|---|
| as shipped | 540 | 19.3 |
| both changes | **98** | **104.8** |

**5.4×**, with all 541 specs and all 68 interaction tests still passing. Combined with §3d's
near-linear scaling to 8 workers, that would put this box around 500–800 real games/s.

The log fix is sound and small. The order cache needs a real invalidation condition — the
scratch version keys on array length alone, which is only safe because nothing leaves the game
in this format. Neither is committed; the branch is clean at `f16e2ea`.

## 9. Minimum state vector for this format

Computed from the pool the 24 archived decks actually use, with ranges checked against 6,681
state samples from 50 real games.

### 9a. The format is far smaller than the card pool suggests

| | |
|---|---|
| distinct cards across all 24 decks | **56** (21 Pokémon, 26 Trainer, 9 Energy) |
| distinct cards in one deck | 13–22, median 18 |
| distinct Pokémon in one deck | 3–6, median 5 |
| Pokémon by stage | 18 Basic, 2 Stage 1, 1 Stage 2 |
| legal slot occupancies | **22** — empty, 18 basics, 3 stacks |
| deepest evolution stack | **2** |
| cards setting a persistent marker | 5 |

Only three evolution stacks exist in the whole field: Jigglypuff→Wigglytuff,
Clefairy→Clefable, and **Squirtle→Blastoise** — Pokémon Breeder skips Wartortle, which never
appears. That is why a slot never holds more than two cards.

Observed bounds (50 games): max 4 Energy on one Pokémon, max 11 damage counters, max hand 25,
max discard 39, max 1 condition at a time, bench fills to 5.

### 9b. Information content

| component | bits |
|---|---|
| stack occupancy (22 states) | 4.5 |
| damage counters (0–12) | 3.7 |
| conditions — asleep/confused/paralyzed exclusive × poisoned | 3.0 |
| **Energy attached** — multisets of ≤6 from 9 kinds = 5,005 | **12.3** |
| markers in effect | 2.6 |
| played this turn | 1.0 |
| **one slot** | **27.0** |
| **× 12 slots** | **324** |
| own hand (multiset over ~18 kinds) | 41.8 |
| opponent hand — size only, contents hidden | 4.7 |
| two discard piles (both public) | 83.6 |
| two deck sizes, two prize counts | 17.5 |
| turn, active player, phase | 9.6 |
| **one player's complete observation** | **482 bits ≈ 60 bytes** |

Energy dominates a slot at 12.3 of 27 bits. Encoding it as 9 independent 0–4 counts costs
20.9 bits — **1.7× worse** — because it ignores that at most ~6 Energy ever sit on one Pokémon.

Two things are *not* stored because they are not information: own deck-and-prize composition is
the decklist minus everything visible, and deck order is unobservable beyond the count. Prize
identities are genuinely unknown to both players, which is a real hidden-information component
of this format, not an encoding choice.

### 9c. As a network input

A one-hot slot is 22 + 13 + 5 + 9 + 5 + 1 = **55 floats**.

| encoding | floats |
|---|---|
| fixed matchup, two known decklists | ~757 |
| any deck built from the 56-card pool | ~871 |
| the full 233-card Base–Rocket+promo pool | ~2,938 |

**~700–900 floats is the working size** — about 60 bytes of actual information, inflated ~12×
by one-hot encoding, which is the usual and reasonable trade. Restricting the vocabulary to the
56 cards the field plays rather than the 233 in the sets is worth **3.4×** on the input layer.
