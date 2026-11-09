# July 2000 STS rules: a testable audit baseline

The July 2000 West Coast Super Trainer Showdown was played under the **DCI Pokémon Floor Rules (file dated 14 Oct 1999)** plus the printed Pokémon rulebook, with WotC's online FAQs and chat rulings settling edge cases. Most of the rules an engine audit needs can be pinned to 2000-dated sources. The key 2000 behaviours are these:
- A mulligan gives the opponent an optional draw of 0 to 2 cards, with no cap on repeated mulligans.
- The player who goes first draws and may attack.
- PlusPower and Defender apply after Weakness and Resistance.
- A Confused Pokémon that fails its flip takes 20 damage, and its own Weakness doubles that.
- Poison and the Asleep flip happen at the end of every turn.
- Toxic Gas ignores all other Powers, including the owner's own.
- Prehistoric Power blocks evolution cards played from hand but not evolution fetched from the deck.

The STS ran 20-minute, single-game Swiss rounds. At time the turn in progress is finished and Prizes are compared, with a win at time worth 2 points and a Prize tie a draw. The weakest items are the rulebook-only ones, because **no scan of the 1999 Base Set rulebook was obtained**. These are one Energy per turn, attacking ends the turn, the exact damage-step list, Sudden Death procedure and the order of between-turns checks. They are marked inferred. Everything dated 2001 or later (Metal and Darkness Energy, "Special Conditions" wording from Jan 2002, flip-first setup from Oct 2000, first-turn attack ban from 2013, first-turn Supporter ban from 2020) must not be used as a 2000 oracle.

Status labels used below:
- **Primary**: WotC/DCI document, or a dated WotC FAQ or chat answer reproduced in the Compendium.
- **Secondary**: a compilation or database, or a player report.
- **Inferred**: deduced from card text or from the absence of a restriction.

## The event and its rule set

The event was the West Coast STS at the Queen Mary, Long Beach, on 22 July 2000. The card pool was Base, Base Set 2, Jungle, Fossil and Team Rocket plus promos, and WotC stated that the event "uses the DCI standard floor rules" ([WotC STS rules, archived 2000-08-18](https://web.archive.org/web/20000818063141/http://www.wizards.com:80/Pokemon/stsrules.asp)). Those floor rules are the [DCI Pokémon Floor Rules, saved 14 Oct 1999 and archived 2000-05-19](https://web.archive.org/web/20000519143655id_/http://www.wizards.com:80/DCI/downloads/Pokemon_Floor_Rules.doc). They were read directly by the research team. Wayback blocked later fetches, so this is a single-read primary source. The East Coast STS (Secaucus, November 2000) had a different card pool (Gym sets) and 25-minute rounds, so it is not this format.

Two sources fill the gaps the floor rules leave. One is the [Team Compendium Rules Compendium](https://compendium.pokegym.net/compendium.html), last updated 11 July 2003. It is a secondary compilation, but each entry is a dated WotC website FAQ or WotC chat answer, and it states that "the rulings that have been gathered from our chats are DCI official." Entries dated on or before 22 July 2000 are 2000-valid, and later ones must be labelled as such. The other is the card data. The [PokemonTCG pokemon-tcg-data repository](https://github.com/PokemonTCG/pokemon-tcg-data) holds printed text and numbers for the six relevant sets: base1 (102 cards), base2 Jungle (64), base3 Fossil (62), base4 Base Set 2 (130), base5 Team Rocket (83 listed, 82 printed) and basep promos (53).

## Setup, mulligans and the first turn

Decks were exactly 60 cards, at most four of any card by English title except basic Energy, with no sideboards (Floor Rules §221 and §222; primary). The pre-game steps in §214 are, in order: determine who plays first; shuffle and offer a cut; draw seven; complete mulligans; choose an Active Basic face down; optionally bench up to five Basics; place six Prizes; flip the Active and Bench Pokémon face up. §213 says the coin-toss winner chooses who plays first.

**Mulligan, verbatim from §215:** a player with no Basic Pokémon "should show his or her opening draw to the opponent, shuffle that hand back into his or her deck, and draw seven new cards. The opponent may now draw up to two extra cards," and the process repeats with up to two extra cards each time. WotC chats in 2000 confirm the draw is optional and can be 0, 1 or 2 ("You MAY draw two extra cards," Mar 2 and Feb 17 chats), that mulligans repeat until both players hold a Basic (Jan 20 chat), and that the hand is drawn before Prizes are placed (Aug 17, 2000 chat) ([Compendium](https://compendium.pokegym.net/compendium.html); primary-derived). Mysterious Fossil and Clefairy Doll are Trainer cards and do not satisfy the Basic check. That ruling rests on a 1999 forum reply, not a WotC document, so its status is secondary.

**Who goes first and when:** the 1999 floor rules list the first-player decision as step 1, before the hands are drawn. The Compendium also records an October 2000 chat saying the new floor rules flip "BEFORE you even draw your hand" (Oct 5, 2000 chat, Q149 and Q181). The two sources conflict about what changed in October 2000, and the notes do not resolve it. Either way the card counts are identical, so treat the order of the flip as untested rather than as a divergence. Later mulligan changes also date from after the STS. The active player resolving mulligans first and the one-extra-card modern rule both come from late 2001 onward.

**First turn:** nothing in the floor rules or Compendium restricts the first player's draw or attack (inferred from absence). The only first-turn limits are on evolution. A Pokémon cannot evolve on the turn it is played, and nothing evolves on the first turn of the game. Eevee's Chain Reaction and Team Rocket Magikarp's Rapid Evolution are exceptions (Jul 27, 2000 chat), and Pokémon Breeder only works when evolution would otherwise be legal. The first-turn attack ban dates from [November 2013](https://bulbanews.bulbagarden.net/wiki/Rules_changing_for_XY_card_game;_Professor_Sycamore_revealed) and the first-turn Supporter ban from 2020. Both are secondary and were seen only as search snippets, and neither applies in 2000. Several turn-structure items come from the rulebook and were not read in a 2000 document, so they are inferred: one Energy attachment per turn and an attack ending the turn. A player who cannot draw at the start of their turn loses ([Basic FAQ via Compendium](https://compendium.pokegym.net/compendium.html); primary-derived).

Other 2000 rulings that bear on turn structure:
- Any number of Trainers per turn, including several PlusPower or Defender (Feb 24 chat).
- Retreat is attempted once per turn. The cost is paid from the retreating Pokémon's Energy, a full Bench does not block it, and retreating clears Poison, Confusion, Sleep and attack effects but not damage (Basic FAQ; Apr 13, 2000 chat).
- Overpaying a retreat cost is not allowed, but the source is dated Aug 2001, so for 2000 it is inferred.

## Damage order, Special Conditions and Confusion

**Damage order.** Weakness (×2) and Resistance (−30) come first, then PlusPower (+10) and Defender (−20) are applied afterwards. The PlusPower ordering is a primary ruling: "the effects of PlusPower are applied after Weakness and Resistance" (Mar 2, 2000 chat). The rulebook's lettered damage list (Weakness and Resistance as steps C and D, Defender-type modifiers at step E) is known only indirectly, from a [Feb 2001 chat](https://compendium.pokegym.net/compendium.html) that contrasts Darkness Energy with Metal Energy, so the structure is secondary and the 1999 wording was not seen. Metal Energy and Darkness Energy are 2001 cards and are outside the pool. The 2003 ruling that Pokémon Powers reducing damage apply after Weakness and Resistance is also later.

**Special Conditions in 2000.** The term "Special Conditions" appears only on 17 Jan 2002. In 2000:
- Asleep, Confused and Paralyzed replace one another, and Poison stacks with any one of them (Feb 17 chat).
- A new Poison replaces the old one rather than doubling (Apr 27, 2000 chat).
- Evolving, retreating or going to the Bench removes the conditions but not the damage.
- A Poisoned Pokémon kept its Powers in 2000. Only Asleep, Confused and Paralyzed switch Powers off, and the printed card texts say so. The 2002 change made Poison and Burn also switch Powers off.

**Between turns.** The notes found no 2000-dated statement of an explicit order between checks (Poison, then Sleep, then Paralysis), so any order is inferred; nothing in 2000 depended on it except a Pokémon that both woke and was knocked out by Poison. What is documented:
- Poison puts 10 damage on the Pokémon at the end of every turn, including the turn it was poisoned (Basic FAQ; Feb 24 chat).
- The Asleep flip also happens at the end of every turn, whoever's turn it was, including the turn the Pokémon fell asleep (Basic FAQ; Feb 10 and May 11, 2000 chats).
- Paralysis wears off at the end of the paralyzed player's own next turn, not at the checkup right after the paralyzing attack (May 18, 2000 chat, Q112).
- Confusion is not a between-turns check.
- A Poison knockout resolves after the turn's win check: "if you win BEFORE the end of the turn, you win, period" (Oct 5, 2000 chat, Q6, consistent with the July rule).
- The modern order of Poison, Burn, Sleep, Paralysis, and promotion after the checks, is a 2024 TPCi ruling and a [Bulbapedia summary](https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_Checkup_(TCG)). Neither is a 2000 rule.

**Confusion.** The coin is flipped before the attack text is carried out (Jul 13, 2000 chat, Q193). On tails the attack does not happen and the Pokémon damages itself. The 2000 amount is **20**, inferred from a ruling that a Confused Kadabra on a failed flip takes 40 (Apr 6, 2000 chat, Q40), meaning 20 doubled by Psychic Weakness. Confusion damage uses the confused Pokémon's own type for Weakness and Resistance (Mar 2 chat), so a Confused Mr. Mime can kill itself (Mar 30 chat). Confusion's 20-damage figure is also stated in an Apr 2001 chat. The [Bulbapedia note](https://bulbapedia.bulbagarden.net/wiki/Special_Condition_(TCG)) that the self-damage later changed (2003) is a search snippet only. One unexplained ruling stays open: a confused Aerodactyl taking no damage (May 11, 2000 chat, Q107). The notes could not reconcile it with the 20-damage rule, so test it separately and do not assume it.

## Winning, Sudden Death, Toxic Gas and Prehistoric Power

**Win conditions** (Basic FAQ): take your last Prize, leave the opponent with no Active and no Bench Pokémon, or have the opponent unable to draw at the start of their turn. The V.3 rulebook said a player with no Pokémon lost at end of turn; WotC corrected this to immediate loss (Feb 17, 2000 chat). A player who draws their last card is not out until their next turn begins (Feb 24 chat).

**Sudden Death.** If both players win at once, the Fossil FAQ says the player who can replace their Active from the Bench wins, otherwise "you play Sudden Death," per the Expert Rules section of the rulebook (primary-derived). That section's text was not found. The procedure of a fresh game with one Prize each is **inferred from memory** and unsourced. A Sep 2001 chat gives a related but different case (a player takes the last Prize and knocks out their own Active with no Bench against an opponent who has a Bench). It is a 2001 ruling and is not to be used as the 2000 test.

**Tournament time rules** (from earlier research on this event, not re-verified in the notes, which built on it):
- Rounds were 20 minutes, one game, same in all three age divisions ([WotC STS rules](https://web.archive.org/web/20000818063141/http://www.wizards.com:80/Pokemon/stsrules.asp)).
- The player in mid-turn (one who has drawn for the turn) finishes that turn. Prizes are then compared, with no extra turns ([Floor Rules §216](https://web.archive.org/web/20000519143655id_/http://www.wizards.com:80/DCI/downloads/Pokemon_Floor_Rules.doc); the STS judge let the turn finish, per [a player report](https://www.pojo.com/Features/0600/0725STSStein.html)).
- A win on Prizes at time scores 2 points, a Prize tie is a draw worth 1 point each, and a full win is 3 points. Bench-outs and deck-outs are full wins. §216 itself says to play on if Prizes are tied, so the STS draw overrides the DCI default. Do not import the modern 40-minute plus 3-turn rule.
- The Swiss ran 8 rounds in the 15-and-over division, planned as 5 or 6. Finals are single elimination and play until one player wins.
- Qualifiers differed: some judges stopped play at once, and a Prize tie went to the larger deck. Those rules are not STS rules.
- Late-arrival Prize penalties apply to humans, not to the engine.

**Toxic Gas and Prehistoric Power.** Printed text (from pokemon-tcg-data, Fossil #13/#28 Muk and #1/#16 Aerodactyl): Toxic Gas reads "Ignore all Pokémon Powers other than Toxic Gases. This power stops working while Muk is Asleep, Confused, or Paralyzed." Prehistoric Power reads "No more Evolution cards can be played. This power stops working while Aerodactyl is Asleep, Confused, or Paralyzed." The primary rulings are:
- Toxic Gas covers the owner's own Powers (Feb 24 chat).
- Two Muks do not cancel each other, so both work (Feb 24 chat).
- A Ditto copying a Confused Muk ends up Ditto (Fossil FAQ).
- The Eevee promo's Chain Reaction still triggers when Grimer evolves into Muk (Sep 7, 2000 chat; after the STS).
- Prehistoric Power cannot be turned off by its owner and blocks Pokémon Breeder and Mysterious Fossil evolutions (Mar 9, Apr 13 and May 18, 2000 chats).
- Fetch-from-deck evolution, such as Rapid Evolution and Chain Reaction, is not "played" and is not stopped (Jul 13, 2000 announcement; Jun 15, 2000 chat).
- Later rulings that Rare Candy overrides Prehistoric Power (2003-2004) and the Shapeshift correction (Nov 2000, Gym cards) are outside the pool.

Nothing in 2000 explicitly says Muk turns off Aerodactyl. By the card text it does, which makes evolution legal again while a healthy Muk is in play. That is inferred, as is the claim that Aerodactyl does not affect Muk.

## Outside references: what to compare, and the caveats

The two sources have different jobs. For field-by-field printed text (HP, types, Weakness, Resistance, retreat, stage, attacks, Pokémon Power text), diff the engine against the raw GitHub JSON at `https://raw.githubusercontent.com/PokemonTCG/pokemon-tcg-data/master/cards/en/<setid>.json`. Prefer it to the pokemontcg.io API, which the docs say works only until 1 March 2027 ([docs](https://docs.pokemontcg.io/api-reference/cards/card-object)). Caveats:
- The JSON has no errata field.
- Missing `retreatCost` means a cost of 0, and missing `weaknesses` means none.
- `damage` is a string that may be empty, `30+`, `×`, `-` or `?`.
- Base Set 2 and Team Rocket reprint earlier names, so resolve cards by card id, not by name.
- Sampled entries matched the printed cards, and a prior engine check found 1 mismatch in 1,926 field checks (Raticate's `?` damage was blank in the engine; cosmetic). The data was not diffed against scans.
- Other text sources (pkmncards, Serebii, Bulbapedia) were not fetched.

For behaviour that printed text does not cover (mulligan option, Confusion damage, Toxic Gas scope, between-turns timing, sudden death), compare against the Floor Rules and the Compendium, filtering to rulings dated on or before 22 July 2000. Caveats:
- It is a secondary compilation last updated in 2003, so it mixes rulings across four years.
- Some entries carry no date.
- The site's search is weak for old cards (a "toxic gas" search returned only modern items).
- Pojo's "Complete Pokemon Card Rulings" (6/12/02) returned HTTP 403 and was not read.
- Neither the Compendium "#errata" section nor the original wizards.com FAQ pages were read.
- Rulebook scans for Base, Jungle, Fossil and Rocket were not obtained, so rulebook-only items stay inferred.

## Conclusion

The audit baseline is firmest where WotC answered a question in 2000 and weakest on what the rulebook says by default. Of the items that most often differ in engines, the mulligan option and the 20-damage self-hit with Weakness doubling are the best sourced. The first-turn attack permission, one-Energy-per-turn, attack-ends-turn and the Sudden Death procedure are inferred, so a mismatch there is a flag to look for a rulebook scan rather than a proven bug. The Aerodactyl confusion ruling and the Muk-versus-Aerodactyl interaction have no clean 2000 answer and should be tested as open questions.

Dating matters more than it looks. Several well-known behaviours (Poison as a Power-disabling Special Condition, flip-before-draw, Metal and Darkness Energy, the 1-card mulligan, no first-turn attack) are all 2001 or later. An engine that matches modern Pokémon rules will disagree with July 2000 in exactly these places, and a checker built from the Compendium without date filtering would import them by mistake.

## Checklist for the implementer

Status: P = primary, S = secondary, I = inferred. Items marked (2001+) are listed only so they are not mistaken for 2000 rules.

1. Deck is exactly 60 cards, max 4 per English title except basic Energy; no sideboard. (P, Floor Rules §221-222)
2. Opening hand is 7 cards; 6 Prizes are placed after Active and Bench are chosen; up to 5 Bench Pokémon. (P, §214)
3. Coin-toss winner chooses who plays first. The flip may precede or follow the draw; assert only that card counts match. (P §213; order conflict noted)
4. A hand with no Basic is shown, shuffled back, and 7 new cards drawn. (P, §215)
5. Each mulligan gives the opponent an optional extra draw of 0, 1 or 2 cards, not forced and not 1. (P, §215; Feb 17 and Mar 2, 2000 chats)
6. Mulligans repeat with no cap until both hands hold a Basic. (P, Jan 20, 2000 chat)
7. Mysterious Fossil and Clefairy Doll do not count as Basics for the mulligan check. (S)
8. The first player draws at the start of turn 1 and may attack on turn 1. (I)
9. No Pokémon evolves on the turn it was played or on the first turn of the game, except Chain Reaction and Rapid Evolution; Breeder only when evolution is legal. (P, Jul 27, 2000 chat; Breeder text)
10. Any number of Trainers per turn; Energy attach is once per turn; an attack ends the turn. (Trainers P; Energy and attack I)
11. Retreat is once per turn, paid from the retreater's Energy, allowed with a full Bench, clears conditions but not damage. (P, Basic FAQ; Apr 13, 2000 chat)
12. Damage order: base damage, Weakness ×2, Resistance −30, then PlusPower +10 and Defender −20. (PlusPower P; Defender and step list S/I)
13. Several PlusPower or Defender cards stack. (P, Feb 24, 2000 chat)
14. Asleep, Confused and Paralyzed replace each other; Poison coexists with one of them; a new Poison replaces the old. (P, Feb 17 and Apr 27, 2000 chats)
15. Evolve, retreat or bench clears the conditions but keeps damage. (P)
16. Poison puts 10 damage at the end of every turn, including the turn it was applied. (P)
17. Asleep flip occurs at the end of every turn, including the turn it fell asleep. (P)
18. Paralysis wears off at the end of the paralyzed player's own next turn. (P, May 18, 2000 chat)
19. Poison does not disable Powers (changes 17 Jan 2002; 2001+ for the opposite behaviour). (I from card text)
20. The Confusion flip comes before the attack text; tails means no attack and 20 damage to self. (P flip order; 20 inferred from the Kadabra 40 ruling)
21. Confusion self-damage applies Weakness and Resistance of the confused Pokémon, so a Confused Kadabra or Mr. Mime takes 40. (P, Mar 2 and Apr 6, 2000 chats)
22. Open item: confused Aerodactyl taking no damage (May 11, 2000, Q107) needs a separate test. (P, unexplained)
23. A win by last Prize or by the opponent having no Pokémon is immediate. A Poison KO after the turn does not cancel a win scored earlier in that turn. (P)
24. Deck-out: a player who cannot draw at turn start loses; a player who draws their last card loses only at their next draw. (P)
25. Both-win-at-once: a player who can promote a Benched Pokémon beats one who cannot; otherwise Sudden Death. The format of Sudden Death is unsourced. (P for the rule, I for the format)
26. Toxic Gas ignores all Powers other than Toxic Gases, including the owner's, and two Muks do not cancel each other. (P)
27. Toxic Gas stops working while Muk is Asleep, Confused or Paralyzed, not while Poisoned. (P card text; Poison I)
28. Prehistoric Power blocks evolution cards from hand, including Breeder and Mysterious Fossil, and cannot be declined by its owner; it stops working while Aerodactyl is Asleep, Confused or Paralyzed. (P)
29. Fetch-from-deck evolution (Rapid Evolution, Chain Reaction) is not blocked by Prehistoric Power. (P)
30. With a healthy Muk in play, Prehistoric Power is ignored and evolution is allowed. (I from card text)
31. Round is 20 minutes, one game; at time the player who has drawn for the turn finishes it, then Prizes are compared. (P)
32. The result at time has three outcomes: more Prizes wins for 2 points, equal Prizes is a draw for 1 point each, a full win is 3 and a loss is 0. Bench-out and deck-out are full wins. (P, with the STS draw overriding §216's play-on default)
33. No +3-turns rule at time (2001+ for modern events); finals do not use the time cut. (I; finals source medium-low)
34. Card definitions match the pokemon-tcg-data JSON for base1 to base5 and basep, matched by card id, not by name. (S)
35. Behaviour tests use only Compendium rulings dated on or before 2000-07-22. (S)
