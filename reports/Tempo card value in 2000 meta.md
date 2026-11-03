# Tempo cards beat Energy only at breakpoints

**Short answer.** In 2000, PlusPower, Gust of Wind, Item Finder and Scoop Up were worth a slot over a basic Energy only in narrow, checkable situations. PlusPower converts a hit into a knockout only when the target is left with exactly 10 HP (or 10 to 20 HP against a Weakness target, if PlusPower is added before Weakness). Gust of Wind creates those situations by choosing the target. Scoop Up and Item Finder protect Prizes and recycle cards. The 25-minute single-game clock turns an early Prize lead into a win. An engine where oracle-timed PlusPower is worth about one Energy may therefore be correct, because PlusPower alone is a narrow card. The thing to test is PlusPower plus Gust of Wind, plus Energy Removal pressure and the clock. **No 2000-era strategy text was read.** pojo.com, Bulbapedia and Pokebeach returned 403 or 404 ([notes](../research_notes/Tempo%20card%20value%20in%202000%20meta/tempo_card_value.md)). Everything about why players valued these cards comes from card text, rulings, 2012 to 2024 retro writers, search snippets, or my memory. Each such claim is tagged below.

Tags: **[read]** a page the note-takers fetched; **[snippet]** seen only in a search result; **[memory]** unsourced recall, verify before use; **[derived]** my arithmetic from card numbers the notes read.

## PlusPower is a +10 that matters only at one remainder

The card numbers the notes read are: Hitmonchan 70 HP, Fighting, Weakness Psychic, Jab {F} 20, Special Punch {F}{F}{C} 40; Electabuzz 70 HP, Lightning, Weakness Fighting, Thundershock {L} 10, Thunderpunch {L}{C} 30, +10 on heads, 10 self-damage on tails ([pkmncards Hitmonchan](https://pkmncards.com/card/hitmonchan-base-set-bs-7/), [pkmncards Electabuzz](https://pkmncards.com/card/electabuzz-base-set-bs-20/)) [read].

Two corrections apply to the notes' own examples. Weakness follows the attack's type, so Thunderpunch (Lightning) doubles against Lightning-weak targets. Hitmonchan's attacks (Fighting) double against Fighting-weak targets, and Electabuzz is one such target. The notes' "Thunderpunch vs a Fighting-weak Basic, 60 to 80" is therefore wrong as stated.

The damage order is the other open point. The notes did not verify it. The project's rules note cites a WotC chat from 2 March 2000: "the effects of PlusPower are applied after Weakness and Resistance" ([Rules Compendium](https://compendium.pokegym.net/compendium.html), via the STS rules note) [secondary compilation of a dated primary chat; I did not see the 1999 rulebook]. I treat that as the likely order, call it **after-order**, and redo each threshold under the alternative, **before-order** (+10 added, then doubled).

| Case [derived] | No PlusPower | 1 PlusPower, after-order | 1 PlusPower, before-order |
|---|---|---|---|
| Thunderpunch (30) vs Lightning-weak 70 HP | 60 (survives at 10) | **70, KO** | **80, KO** |
| Thunderpunch, heads (40) vs same | 80, KO | 90 | 100 |
| Jab (20) vs Electabuzz (Fighting-weak, 70 HP) | 40 | 50 | 60, no KO |
| Special Punch (40) vs Electabuzz | 80, KO | 90 | 100 |
| Special Punch (40) vs neutral 70 HP | 40 | 50, no KO | 50, no KO |
| Special Punch vs neutral 50 HP | 40 | **50, KO** | **50, KO** |

Two rules fall out of the table. Under after-order, PlusPower flips a result only when the target would be left with exactly 10 HP, since HP and damage come in tens. Under before-order, a Weakness target flips at 10 or 20 HP left. The 70-HP Lightning-weak case crosses under both orders, so that part of the notes' point survives, with the right type. Stacking is allowed: "multiple PlusPower per turn: Yes (Feb 24 WotC Chat)" ([Rules Compendium](https://compendium.pokegym.net/compendium.html)) [secondary]. Two PlusPower take a neutral 40-damage Special Punch to 60. Which Basics carry Lightning Weakness (Magikarp, Seel, Staryu and similar) is **[memory]**: the notes read no such card. Check the engine's card data (base1 to base5 JSON) for every Lightning-weak Basic and its HP before trusting the first row.

## Gust of Wind chooses the target, so it, not PlusPower, makes the breakpoints

Gust of Wind switches an opposing Benched Pokémon with the Active one ([pkmncards](https://pkmncards.com/card/gust-of-wind-base-set-bs-93/)) [read]. Haymaker writers pair it with PlusPower or Energy Removal "to take an easy early Prize" ([Haymaker World](https://haymakerworldtcg.squarespace.com/blog/what-is-a-haymaker-deck)) [snippet; late source]. The logic is [derived]. An oracle-timed PlusPower can only pick the turn it is played. A Gust of Wind picks which Pokémon is hit. It can drag up the Lightning-weak 70 HP Basic or the already-damaged Basic that sits at exactly 10 HP remaining. The two cards are worth far more together than separately, so the human median of about 2.75 PlusPower to 2.5 Gust looks like a matched pair. If the engine's marginal-value test removes PlusPower alone against a field where Gust is absent or unused, it measures the weak half. Test PlusPower and Gust of Wind jointly, and also with the opponent's bench forced to hold a Weakness or damaged Pokémon.

## Scoop Up, Item Finder and the draw Trainers protect Prizes and cards

Scoop Up returns a Pokémon's Basic card to hand and discards everything attached ([pkmncards](https://pkmncards.com/card/scoop-up-base-set-bs-78/)) [read]. Against a six-Prize race this denies a Prize on a damaged Pokémon, at the cost of its attached Energy ([derived], from the card text; no 2000 writer was read). It is therefore the natural answer to a PlusPower-boosted attacker, and it makes extra Energy on one Pokémon a risk. Item Finder, Professor Oak, Bill and Computer Search are all **[memory]** here: the notes quote none of their text, and the Item Finder page returned 404. My recollection is that Item Finder recycles a Trainer from the discard pile at the cost of another Trainer, Oak and Bill draw, and Computer Search discards two cards to fetch any card. Their shared role would be to trade a card slot for hand quality, which an Energy slot cannot do. The 2012 Haymaker list also runs 3 Oak, 3 Bill, 2 Item Finder and 2 Scoop Up ([PokeBase](https://pokemondb.net/pokebase/57873/what-is-a-haymaker-tcg-deck)) [read; a 2012 answer]. That list has 23 Energy and 25 Trainers and is not a 2000 STS list, which the project already treats as different rather than conflicting. The 2000 human medians (18 Energy, 28 Trainers) leave a deck with five fewer Energy and three more Trainers than that list.

## The clock and Energy Removal set the tempo

The West Coast STS (Long Beach, 22 July 2000) is reported as Swiss, single game, 60 cards, 6 Prizes, 25-minute limit ([pokumon archive](https://pokumon.com/super-trainer-showdown-2000/)) [snippet]. The DCI floor rules of October 1999 give one game per match, a recommended 25 minutes, and at time the player with fewer Prizes remaining wins after the current turn ([DCI Floor Rules](https://web.archive.org/web/20000519143655id_/http://www.wizards.com:80/DCI/downloads/Pokemon_Floor_Rules.doc)) [read, primary; sections 211, 212, 216]. The project's C02 work says the STS scored a Prize tie as a draw, though the floor rules would continue the game. A prize lead at time is a win, so a fast first knockout is valuable beyond the six-Prize race, and PlusPower plus Gust is the cheapest way to get one. East Coast (Secaucus, Nov 2000) reportedly used Prop 15, with at most 15 Trainers ([archive](https://alexwilsonnc.github.io/tes/major-events/2000/nj-super-trainer-showdown/summary)) [snippet]. A median of 28 Trainers cannot come from East lists, so check how many of the 24 lists are East and whether their Trainer counts are at most 15.

Energy Removal pressure is the other half. The 2012 Haymaker list runs 4 Energy Removal and 4 Super Energy Removal ([PokeBase](https://pokemondb.net/pokebase/57873/what-is-a-haymaker-tcg-deck)) [read; 2012]. No 2000 source quantifies Energy Removal or how it changed the right Energy count, so any claim that it lowered the Energy count is an inference. The mechanism is plausible and checkable: a deck facing Energy Removal wants Energy to be replaceable, and an Energy Removal that fires on the attacker also cancels the PlusPower. Hold the opponent's Energy Removal rate as a parameter.

## Conditions to compare against the engine

| # | Condition (all derived or ruled, not sourced to 2000 strategy writing) | What to check in the engine |
|---|---|---|
| 1 | Damage order: PlusPower after Weakness/Resistance (Mar 2000 chat, secondary) | Engine order; rerun the table above with the other order if it differs |
| 2 | PlusPower flips a KO only at 10 HP left (after-order), or 10 to 20 on Weakness (before-order) | Fraction of PlusPower plays that change a KO; counters and Poison make 10-remainders |
| 3 | Weakness type follows attack type (Thunderpunch Lightning, Special Punch Fighting) | Engine's Weakness lookup; list of Lightning-weak Basics and their HP |
| 4 | Multiple Trainers per turn, so stacked PlusPower is legal | Engine allows more than one PlusPower a turn |
| 5 | Gust is the target selector; test the PlusPower and Gust pair | Joint ablation, bench contents forced |
| 6 | Time cut: 25 minutes, fewer Prizes wins, Prize tie a draw at STS | Engine clock and tie rule; share of games decided at time |
| 7 | Pre-2000-October rules: mulligan optional draw up to 2, no first-turn attack ban | Engine setup; first-player bias |
| 8 | Scoop Up discards attached cards; Basic returns to hand | Engine's handling of evolution cards, Energy, damage |
| 9 | Energy Removal density in the field (unquantified for 2000) | Opponent pool's Energy Removal count and its effect on PlusPower and Energy value |
| 10 | Lists: median 13.5 / 28 / 18; East lists at most 15 Trainers | Per-list Trainer counts by event |

## What the evidence supports and what it does not

The strongest finding is arithmetic: PlusPower is a +10 whose value depends on remainders and order, and the notes' headline example had the wrong Weakness type. The weakest claims are the "why players valued it" ones, because they rest on late retro writers and snippets. A reading of The Duelist, a 2000 tournament report or the pojo archive would settle whether players described Gust plus PlusPower as the early-Prize engine. Until then, the engine result (PlusPower about one Energy) is consistent with the card text, and the open question is whether the engine's Gust, Energy Removal, clock and damage-order settings match the table above.
