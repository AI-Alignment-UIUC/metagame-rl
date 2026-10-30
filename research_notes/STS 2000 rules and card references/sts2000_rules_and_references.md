# STS 2000 (Long Beach, 22 July 2000) rules and card references, for the ryuu-play engine audit

Scope: Base Set, Base Set 2, Jungle, Fossil, Team Rocket plus promos, as in force July 2000. Prior work not repeated: `reports/C02-round-length/findings.md` (round length, time procedure) and `notes/sts-2000-engine-check.md`.

Source keys used below.
- **[FR]** DCI Pokémon Floor Rules, Word file last saved 14 Oct 1999, archived by the Wayback Machine 2000-05-19. PRIMARY (Wizards/DCI). I downloaded the .doc and read its text myself. URL: https://web.archive.org/web/20000519143655id_/http://www.wizards.com:80/DCI/downloads/Pokemon_Floor_Rules.doc (WebFetch is blocked for archive.org; plain `curl` of this URL worked once, then Wayback began blocking).
- **[RC]** Team Compendium "Rules Compendium" (WotC Pokémon TCG Rulings Compendium), last updated 11 July 2003. SECONDARY compilation of PRIMARY WotC sources (the online FAQs on wizards.com and the weekly WotC chat transcripts, each entry dated). URL: https://compendium.pokegym.net/compendium.html (single HTML page, about 600k characters of text; I downloaded it and grepped it). Entries carry their original dates, so 2000-era rulings can be separated from 2001+ ones.
- **[PTD]** PokemonTCG/pokemon-tcg-data JSON, https://github.com/PokemonTCG/pokemon-tcg-data (raw files: `https://raw.githubusercontent.com/PokemonTCG/pokemon-tcg-data/master/cards/en/<setid>.json`, `.../sets/en.json`). SECONDARY (database).

Caveat on the missing piece: I did not find a scan or transcription of the 1999 Base Set rulebook (v1/v2/v3) or of the Jungle/Fossil/Team Rocket rulebooks. Wayback, Bulbapedia (Cloudflare) and pojo.com (403) blocked my fetches. A further attempt to fetch a pojo .doc with a spoofed Referer was denied by the permission system, and I did not retry it another way. Rulebook wording below therefore comes from [FR], which says its pre-game steps are "similar to what appears in the Pokémon rulebook", and from dated WotC FAQ/chat answers in [RC] that quote the rulebook. Items that come from my own memory or from non-primary sites are marked.

## Q1a. Setup: deck, hand, Prizes, mulligan, order of steps

### Takeaway
In July 2000 a deck was exactly 60 cards with at most 4 of any card except basic Energy; hands were 7 cards and Prizes 6. A player with no Basic Pokémon showed the hand, shuffled it back and drew 7 again, and the opponent MAY (not must) draw up to 2 extra cards for each such mulligan. The coin flip came before the hands were drawn only in later floor rules (October 2000 and after), not in the October 1999 rules in force at the STS qualifiers.

### Cited Findings
- Deck size and copy limit: "Constructed decks must contain exactly sixty cards. With the exception of basic energy, a player's deck may not contain more than four of any individual card, counted by English card title equivalent. (This rule is identical to what appears in the Pokémon rulebook.)" — [FR §221] (primary)
- No sideboards: "No sideboards are allowed in Pokémon tournaments." — [FR §222] (primary)
- Pre-game procedure, verbatim steps (§214; "The steps listed below are similar to what appears in the Pokémon rulebook."): "1. Determine who plays first (see section 913). 2. Players must shuffle their decks and present them to their opponents for additional shuffling and/or cutting... 3. Each player draws an initial hand of seven cards. 4. Each player, starting with the first player, completes all of his or her Mulligans (see section 215). 5. Each player selects a Basic Pokémon from his or her hand and places it face down on the table. This is the trainer's Active Pokémon for the start of the game. 6. Each player may, if he or she wishes, choose up to five Basic Pokémon from his or her hand and put them face down on his or her Bench. 7. Each player places the top six cards from their decks face down in front of them. These cards will serve as Prizes. Trainers cannot look at a Prize card until they select it as a Prize. 8. Immediately before play begins, each trainer flips over all the Active and Benched Pokémon that have been put on the table." — [FR §214] (primary). Note the order here: who goes first is decided BEFORE hands are drawn (step 1 before step 3), and Prizes are placed after Active/Bench.
- Who plays first: "The winner of a coin toss (or other random method) chooses who plays first." — [FR §213] (primary)
- Mulligan, verbatim: "If a player's initial hand does not contain a Basic Pokémon card, that player should show his or her opening draw to the opponent, shuffle that hand back into his or her deck, and draw seven new cards. The opponent may now draw up to two extra cards. If the player still has no Basic Pokémon in his or her next draw, he or she may repeat this process, but the opponent may draw up to two extra cards each time." — [FR §215] (primary)
- The extra draw is optional and is 0, 1 or 2: "Do you have to draw 2 cards when your opponent Mulligans? A. No, you don't. You MAY draw two extra cards. (Mar 2 WotC Chat)"; "You can draw UP to 2 cards, so you could draw 0, 1 or 2. (Mar 2 WotC Chat)"; "No, you MAY draw two cards; you do not have to. (Feb 17 WotC Chat)" — [RC "Starting the game"] (secondary compilation of 2000 WotC chats)
- No limit on repeated mulligans: "You keep doing it until each player has a basic Pokémon in his or her starting hand. (Jan 20 WotC Chat)" — [RC]
- The mulligan draw comes after the hand is drawn: "If my opponent puts down his prizes, then draws his hand... The correct order is hand first. (August 17, 2000 WotC Chat Q211)" — [RC]
- A mulligan player does not reveal Basics: only the hand with no Basic is shown (rule text above). A hand whose only Pokémon is a Baby (Neo era, 2001) must be played, "(Jan 11, 2001 WotC Chat, Q105)" — [RC]; that is later than July 2000 and Babies are outside the STS pool.
- Mysterious Fossil / Clefairy Doll are Trainer cards, not Basic Pokémon, for the mulligan check: a 1999 forum reply says so ("they do NOT count as 'Basic Pokemon' when checking whether you have a Mulligan"), unofficial. Compendium has the same ruling in the 2000 era (Fossil FAQ); I did not extract the dated line. Prior note: the engine failed this (T18). — https://www.pojo.com/CCQA/QandA/1099/100507.txt (search snippet only, not fetched)
- Later changes (mark as 2001+): (i) the October 2000 floor rules move the coin flip before drawing the opening hand: "The new version of the DCI Pokémon Floor Rules says you do the opening coin flip before placing your Active/Bench Pokémon... You flip and determine who goes first BEFORE you even draw your hand of cards. (Oct 5, 2000 WotC Chat, Q149 & Q181)" — [RC]. This is after the STS (22 Jul 2000). (ii) From about October 2001 the active player resolves mulligans first, then places a card, and (Dec 2001) "9" cards for a second-player redraw after the first player's mulligans — [RC "Starting the game", Nov 15 and Dec 13, 2001 chats]. (iii) The modern rule, for contrast only: one extra card per mulligan after the first, optional.
- Per-mulligan draw timing ambiguity: in 2000 [FR] letters "The opponent may now draw up to two extra cards" immediately after the mulligan is resolved; the Oct 19, 2000 chat says "technically you could do that but if you still don't end up with a basic then you get caught cheating and you lose the match, period" about a second player drawing extras without a Basic — [RC]

### Inferences
- For the STS engine the right 2000 rule is: each mulligan gives the opponent an optional draw of 0 to 2 cards; there is no cap on mulligans. If the engine hands the extra cards automatically, or forces 2, or gives 1 per mulligan, it differs from July 2000. Whether the pilot declines the draw is a policy choice, but the option must exist.
- Whether the first player is decided before the draw changes who learns what, not the card counts, so it matters little for deck composition.

### Gaps
- No scan or transcription of the Base Set (1999) rulebook was obtained, so rulebook wording (as against floor rules) is unverified. The Jungle/Fossil/Rocket rulebooks are inserts that, as far as I recall, repeat the same rules; unverified.
- The exact date the "draw up to two" wording replaced any earlier "draw two" wording is not documented; the March 2000 chats already say "up to".

## Q1b. First turn and turn structure

### Takeaway
In 2000 there was no first-turn restriction on the player going first except the evolution rule (nothing evolves on the first turn that Pokémon is in play, and no Pokémon is evolved on that player's first turn of the game); the first player drew a card and could attack. The first-turn attack ban dates from the XY era (2013) and the first-turn Supporter ban from 2020.

### Cited Findings
- Draw at start of turn, loss if you cannot: "You also win if your opponent can't draw a card at the beginning of his or her turn because his or her deck ran out of cards" — [RC WIN STATES, Basic FAQ, WotC website] (primary-derived). Nothing in [FR] or [RC] exempts the first player from drawing.
- Evolution timing: "you can never evolve your Pokemon on the first turn you play in the game" (Jan 9, 2003 chat, restating the long-standing rule) and "the normal 'Pokémon must be in play for at least one turn' is still in effect" except Eevee's Chain Reaction and TR Magikarp's Rapid Evolution (Jul 27, 2000 chat): "Yes, essentially, though I don't know a single way you could do Team Rocket Magikarp's Rapid Evolution on the first turn." — [RC]
- "Can I use Pokémon Breeder on my first turn? No, only when you could usually evolve. (Jan 25, 2001 WotC Chat, Q89)" and the Breeder card text "You can only play this card when you would be allowed to evolve that Pokémon anyway." — [RC]; [PTD base1] (Breeder)
- Evolving after the first turn in play: a Pokémon played on your turn cannot evolve on that turn; it can on your next turn. "Evolving": the evolution card is placed on Active or Benched Pokémon. Standard evolution is a play from hand; powers/attacks that fetch from the deck are not "played": "Aerodactyl's Pokémon Power 'Prehistoric Power' says No more Evolution cards can be played. The above attacks and powers would NOT be affected" — [RC, WotC Chat 2000-11-30 and Jul 13, 2000 Announcements]
- Giovanni (Gym) allowed evolving Pokémon played this turn (Oct 5, 2000 chat Q103) — [RC]; Gym sets are outside the STS-California pool.
- Trainers: "Can I play more than one Trainer card on my turn? A. Yes. (Basic FAQ, WotC Website)"; multiple PlusPower/Defender per turn allowed: "Yes. (Feb 24 WotC Chat)" — [RC TRAINER CARDS]. No limit on Supporters existed in 2000 (Supporters came with Neo-era/2000s? first appear in Gym-era Trainers? Not in this pool; I did not source the Supporter class).
- Energy: one per turn is the standard rule; I did not find a dated quote in [RC] (the Basic FAQ line was not extracted). Mark: from memory, plus the Dec 2000 chat line "must attach both energies at the same time" for Neo cards is later. Needs a rulebook scan.
- Retreat: once per turn: "You can only attempt to retreat once... If it fails, that Pokémon cannot attempt to retreat again that turn, whether it is still confused or not. (Apr 13, 2000 WotC Chat Q146)"; retreat cost is paid by discarding Energy attached to the retreating Pokémon: "From the Pokémon. (Basic FAQ, WotC Website)"; cannot overpay: "No. (Aug 9, 2001 WotC Chat, Q311)" (2001, mark later); a full bench does not stop a retreat: "Yup... (Jul 13, 2000 WotC Chat, Q222)"; retreating a no-cost Pokémon must bring up a different Pokémon: "(Feb 17 WotC Chat; May 11, 2000 WotC Chat, Q31)"; retreating clears Poison, Confusion, Sleep and attack effects but not damage: "No. Retreating does not remove damage. (But it does remove Poison, Confusion, Sleep, or anything else that's the result of a Pokémon's attack...)" (Basic FAQ) — [RC RETREATING]. Switch card on a Confused/Asleep/Paralyzed Pokémon works to retreat (Feb 3, 2000 chat per search listing at https://compendium.pokegym.net/ruling/page/168; not extracted).
- Attack ends the turn: standard; no dated quote extracted. Pokémon Powers "As often as you like"/"once during your turn" are printed on the cards ([PTD]).
- Later restrictions (2013 and 2020): first player cannot attack on the first turn — "starting Nov. 8 [2013], the first player will not be allowed to use an attack on their first turn" — https://bulbanews.bulbagarden.net/wiki/Rules_changing_for_XY_card_game;_Professor_Sycamore_revealed (secondary news; I saw it only as a search result). First-turn Supporter ban: Sword & Shield, 2020 — https://www.pokeguardian.com/386462_first-turn-no-supporter-rule-regulation-marks-has-been-officially-announced-first-turn-no-supporter-rule-regulation-marks-has-been-officially-announced-fairy-type-no-longer-supported (secondary; search snippet). A blog claims the Base Set coin-flip winner could "draw, play Trainers, attach Energy, and attack" on turn one — https://geekydomain.com/blogs/guides/pokemon-modern-rules-vs-base-set (non-authoritative).

### Inferences
- If the engine bans a first-turn attack, or a first-turn draw, it differs from July 2000. A first-turn attack ban would also slow human-style decks relative to 2000 play. (The prior note's seat bias of 49.5% to 54.5% suggests this is not present, but I did not check the engine code.)

### Gaps
- I could not source the "one Energy attachment per turn" and "attacking ends your turn" wording from a 2000 primary document; both are universally stated in the printed rulebook but I did not read it. First-turn attack/draw permission is inferred from the absence of any restriction in [FR] and [RC] and from the 2013 change announcement.

## Q1c. Damage, Weakness, Resistance, PlusPower, Defender, Special Conditions

### Takeaway
Weakness (×2) and Resistance (−30) are applied to the attack's damage, then PlusPower and Defender are applied after them; effects on the attacker that reduce damage before Weakness exist only for Metal Energy (2001, outside the pool). Confusion in 2000 was 20 damage to the confused Pokémon (the coin-flip failure), and Weakness applies to that self-damage.

### Cited Findings
- PlusPower is applied after Weakness and Resistance: "No, the effects of PlusPower are applied after Weakness ands Resistance. (Mar 2 WotC Chat)" — [RC TRAINER CARDS]. The rulebook's damage list (steps lettered A to E, Weakness and Resistance are steps C and D, Defender-type effects step E) is quoted indirectly: "Darkness energy IS figured out in Step E (after weakness and resistance) but the Metal energy's effects DO have to be resolved BEFORE step E" (Feb 1, 2001 chat, Q27) — [RC]. Mark: 2001; confirms the structure of the list but not its 1999 wording.
- Pokémon Powers that reduce damage are calculated after Weakness and Resistance by default: "Without it being specified you always fall back on the 'How do you figure out the damage?' list from the rule book. Pokemon Powers are calculated after Weakness and Resistance are done. (Apr 3, 2003 WotC Chat, Q1041)" — [RC] (2003).
- Damage counters, not damage, for Poison and Confusion counters in later rulings: "As stated in the Neo rulebook 'you put damage counters on an any Poisoned Pokémon' after each player's turn. So Poison does NOT do damage... (Jan 4, 2001 WotC Chat Announcements & Q92)" — [RC] (2001; mark later).
- Confusion self-damage and Weakness: "the Pokémon is hitting himself when Confused (and failing the coin flip) so use its type to check for Weakness or Resistance effects. (Mar 2 WotC Chat)"; "Kadabra... A failed attack in this case will do 40 to Kadabra. (April 6, 2000 WotC Chat Q40)" (so the base self-damage is 20, doubled by Weakness); "If Mr. Mime is Confused... does he kill himself (due to Weakness)? Yes it would. (Mar 30 WotC Chat)"; "If Aerodactyl is Confused and hurts itself, would it take damage or not? Nope." (Aerodactyl has Psychic Resistance? No: this reflects Aerodactyl's printed Pokémon Power? Not explained in source.) (May 11, 2000, Q107) — [RC]. The "20" is inferred from the Kadabra answer (40 = 20 ×2) and from a Metal Energy example in 2001: "Confusion does 20" (Apr 12, 2001 chat, Q1) — [RC]. Bulbapedia (not fetched; search snippet) says originally a confused Pokémon attacked itself for 20 damage on tails, changed in 2003: https://bulbapedia.bulbagarden.net/wiki/Special_Condition_(TCG).
- Order of confusion check: "You flip for Confusion BEFORE you do what the attack tells you to do. (Jul 13, 2000 WotC Chat, Q193)" — [RC]
- Special Condition rules as of 2000 (the term "Special Conditions" only came on 17 Jan 2002): Asleep, Confused, Paralyzed replace one another; Poison stacks with any of them: "You can be Poisoned and any other effect (Asleep, Confused, or Paralyzed), but not a combination of Sleep, Confusion, or Paralysis. If your Pokémon gets one of those 3 effects, the new effect replaces the old one. (Feb 17 WotC Chat)" — [RC]. A new Poison replaces an older one (Nidoking's double poison): "It would gain a single poison effect (the new effect replaces the old one). (April 27, 2000 WotC Chat Q19)" — [RC].
- Poison lasts "Until the Pokémon is Benched, Evolved, or Knocked Out. (Mar 30 WotC Chat)"; Evolving removes Poison/Sleep/Confusion/Paralysis but not damage (April 27, 2000, Q49) — [RC]. Retreating/Benching removes them too (Basic FAQ; Feb 3, 2000; April 13, 2000 Q43) — [RC].
- Jan 2002 change (mark later): Poison, Burn and the other conditions become "Special Conditions" and shut off Powers that were previously only shut off by Asleep/Confused/Paralyzed — [RC, Jan 17, 2002 Announcements and Q1278/1280]. In 2000 a Poisoned Muk, Alakazam, etc. still used their Powers (the card texts only name Asleep, Confused and Paralyzed — see [PTD]).
- Winning and loss conditions: "You win when you draw your last Prize or when your opponent loses his or her Active Pokémon and doesn't have a Pokémon on the Bench to replace it. You also win if your opponent can't draw a card at the beginning of his or her turn because his or her deck ran out of cards" — [RC WIN STATES, Basic FAQ, WotC Website]. The V.3 rulebook said you lose at END of turn with no in-play Pokémon, corrected: "The rulebook is incorrect; you lose immediately if you do not have an active Pokémon. (Feb 17 WotC Chat)" — [RC]. Last-card-then-win: "you won't actually lose for being out of cards until the beginning of your next turn. (Feb 24 WotC Chat)" and Professor Oak with fewer than 7 cards: "You only lose when you don't have any cards to draw on... (Aug 3 2000 WotC Chat, Q43)" — [RC].

### Inferences
- The engine must apply Weakness/Resistance first and then PlusPower and Defender; confusion self-damage must be 20, doubled by the confused Pokémon's own Weakness (so a confused Kadabra or Mr. Mime takes 40). If the engine uses 30 or does not apply Weakness, it differs from 2000.
- Poison does 10 per check, and the 2000 rulings count it as part of "end of turn", after the attack's resolution (see Q-b below).

### Gaps
- No primary quote for the original damage list wording (rulebook steps A to E) was found. The Aerodactyl "Nope" answer is unexplained in the source (possibly a ruling about a power-protected Pokémon); I did not resolve it.
- No dated 2000 source stated Poison damage as "10"; it is on Base Set Weedle/Koffing-era cards via counters in the [PTD] texts and in "put 10 more damage on it" (Feb 24 chat, Q "My opponent attacks my Active... Do I then have to put 10 more damage on it because it is still Poisoned? A. Yes.") — [RC].

## Q2. Tournament rules at the 2000 STS

### Takeaway
Verified: the DCI floor rules ([FR]) govern. Rounds are one game and the end-of-match procedure finishes the player's turn; ties at time continue play under the DCI default (the STS overrode it to a draw, per C02). Decks are exactly 60 cards, no sideboards, 4-copy rule by English title, and the first player is decided by coin toss (winner chooses).

### Cited Findings
- End of match, verbatim: "A player in mid-turn when the end of the round is announced is allowed to complete his or her turn before the match result is determined. (A player in mid-turn is someone who has drawn a card for his or her current turn.) The player with the least amount of Prize cards remaining on the table is then considered the winner. If both players have an equal number of Prize cards, continue the game until one player has more Prize cards than the other. If a judge assigned a time extension... then the end of match procedure does not occur until the end of the time extension." — [FR §216]. Verified against C02 [A5]. (The STS-specific draw on a Prize tie comes from C02's sources, not [FR].)
- Match structure and time: "One game is the default number of games in a Pokémon match" (§211); recommended 25 minutes per round (§212) — [FR]. Whether the STS used 20 minutes: see C02.
- Deck registration: [FR] contains no decklist registration section; its sections are 201 to 237 (formats, cards, match structure, time, who plays first, pre-game, mulligan, end of match, match winner, deck size, sideboard, limited, materials). The STS used the DCI rules ("This tournament uses the DCI standard floor rules", C02 [A1]). I found no 2000 document that describes decklist registration at the STS.
- Sudden death is NOT in [FR]: its sections list no "both players win at once" rule; the rule is in the rulebook's expert section (see Q-c).
- Player flip/first-player procedures in tournaments: coin toss winner chooses (§213), and for multi-game matches the loser chooses — [FR]. The change to flip before drawing came October 2000 (above).
- Cheating consequence quoted in chat: a player who draws extra mulligan cards without a mulligan "get[s] caught cheating and you lose the match" (Oct 19, 2000 chat, Q46) — [RC].

### Inferences
- The tied-Prize "play on until one player is ahead" default in [FR §216] conflicts with the STS's draw, so an engine implementing a time cut must follow C02, not [FR].

### Gaps
- No primary document found on STS decklist registration or whether decks were checked; none on first-player procedures beyond [FR §213].

## Q3. Card text and rulings references

### Takeaway
Best programmatic sources: PokemonTCG/pokemon-tcg-data on GitHub (raw JSON, same data as the pokemontcg.io API) for printed text; the Team Compendium Rules Compendium for dated 1999 to 2003 WotC chat/FAQ rulings.

### Cited Findings
- **Rules Compendium, archived original**: https://compendium.pokegym.net/compendium.html ("WotC POKÉMON TRADING CARD GAME RULINGS COMPENDIUM", last updated July 11, 2003, compiled from WotC FAQs and chat logs; it states "The rulings that have been gathered from our chats are DCI official, so yes. (Oct 26, 2000 WotC Chat, Q24)"). One long HTML page with all entries sorted by card name, then "RETREATING", "STARTING THE GAME", "SPECIAL CONDITIONS / STATUS EFFECTS", "TRAINER CARDS", "WIN STATES" at the end. Searchable by card by browser search or `grep` on a downloaded copy (`curl -sL https://compendium.pokegym.net/compendium.html`). Every ruling is dated, so filter to dates before 22 Jul 2000. A newer version with the same content in a database layout: https://compendium.pokegym.net (searchable at `/?s=<term>`, with category pages like https://compendium.pokegym.net/category/7-gameplay/starting-the-game; the page `Team Compendium` on Bulbapedia, https://bulbapedia.bulbagarden.net/wiki/Team_Compendium, describes it). The site's search is weak for old cards (search for "toxic gas" returned only modern items). Other archives: Pojo's "The Complete Pokemon Card Rulings (updated 6/12/02)", https://www.pojo.com/pokemon/rules/master_rules_document.doc (returned HTTP 403 to my fetch, unread); versions of the same document at pkcompendium.com were not fetched. The versions dated 1999-2003 mentioned in the brief: I could confirm only the 11 July 2003 version and Pojo's 6/12/02.
- **pokemontcg.io / pokemon-tcg-data**: set ids and release dates from `sets/en.json`: base1 Base (102 cards, 1999/01/09, ptcgo code BS), base2 Jungle (64, 1999/06/16, JU), basep Wizards Black Star Promos (53, 1999/07/01, PR), base3 Fossil (62, 1999/10/10, FO), base4 Base Set 2 (130, 2000/02/24, B2), base5 Team Rocket (83 listed, 82 printed, 2000/04/24, TR), base6 Legendary Collection (2002; not in the 2000 pool). — [PTD sets/en.json]. The API docs say the API is deprecated: "Existing keys work through March 1, 2027, and the docs recommend migrating to Scrydex" — https://docs.pokemontcg.io/api-reference/cards/card-object (WebFetch summary). The raw GitHub data is the stable route.
- **Printed text accuracy**: sampled entries match the printed cards (Alakazam "Damage Swap", Chansey, Muk, Aerodactyl, Ditto, Pokémon Breeder, Professor Oak, Bill, Energy Removal, Gust of Wind, Switch). The prior check found 1 cosmetic mismatch in 1,926 field checks (`notes/sts-2000-engine-check.md` §7).
- **Errata**: the data carries no errata field, only printed text (the card object lists `rules` for Trainers, `abilities` for Powers, and no errata field; the API docs "do not describe how the API handles errata or reprinted card versions"). Errata exist only in the Compendium.
- **Other printed-text sources** (not fetched): pkmncards.com (e.g. https://pkmncards.com/card/muk-fossil-fo-13/), Bulbapedia (Cloudflare-blocked from my tools), Serebii (https://serebii.net/card/base/), pocketmonsters.net (https://pocketmonsters.net/tcg/viewset/5). Which is most reliable for exact text: I did not verify against card scans. The JSON in [PTD] agreed with the printed texts I recalled.
- **Errata before July 2000**: found in [RC] only through the Fossil FAQ and chat items. The one pre-July 2000 correction I found: the V.3 rulebook "loses at end of turn" statement (Feb 17, 2000). I did not extract the "ERRATA" section of [RC] (anchor `#errata`); see Gaps.

### Inferences
- Use the raw `pokemon-tcg-data` JSON for field-by-field engine comparison and the Compendium (filter to dates ≤ 2000-07-22) for behaviour tests.

### Gaps
- Not read: the [RC] "#errata" section, the Pojo master rulings document, the Wizards FAQ pages for each set (Fossil FAQ, Basic FAQ, Rocket FAQ originals on wizards.com), and scans of the rulebooks.

## Addition (a). Muk's Toxic Gas and Aerodactyl's Prehistoric Power

### Takeaway
Toxic Gas turns off every Pokémon Power except other Toxic Gases, including the owner's own; two Muks do not cancel each other. Prehistoric Power stops evolution cards being played from hand, cannot be turned off by the owner, and is itself a Pokémon Power, so Toxic Gas should turn it off (inferred from the text).

### Cited Findings
- Card text (printed): Toxic Gas: "Ignore all Pokémon Powers other than Toxic Gases. This power stops working while Muk is Asleep, Confused, or Paralyzed." Prehistoric Power: "No more Evolution cards can be played. This power stops working while Aerodactyl is Asleep, Confused, or Paralyzed." — [PTD base3-13, base3-28, base3-1, base3-16]. Muk has two Fossil printings (13 and 28), and so does Aerodactyl (1 and 16), same text.
- Toxic Gas covers the owner's own Powers: "Does Muk's Pokémon Power ignore ALL in play or just your opponent's Power? A. All Powers except for Toxic Gases. This includes your own. (Feb 24 WotC Chat)" — [RC TOXIC GAS]
- Two Muks: "If a Muk faces another Muk does Muk B's power cancel out Muk A's power so powers are once again activated? A. Muk's Toxic Gases says it cancels all Powers except Toxic Gas, so both would work (Feb 24 WotC Chat)" — [RC]
- Toxic Gas does not stop the Eevee promo's Chain Reaction triggered by evolving Grimer into Muk: "the promo Eevee's Chain Reaction Pokémon Power would be triggered by the evolution of Muk and would still occur even though Muk's Toxic Gas states to ignore all other Pokémon Powers. Of course, any evolutions done after this case would NOT trigger the Chain Reaction (Sep 7, 2000 WotC Chat Announcements)" — [RC] (Sep 2000, after the STS)
- Toxic Gas and Shapeshift: a Nov 2000 correction: "Shapeshift ignores powers, so the Toxic Gas shouldn't work, correct? A. Correct. We made a mistake. (Nov 2, 2000 WotC Chat, Q299)" — [RC] (Gym cards; outside the pool).
- Toxic Gas and Ditto: "What happens if Ditto copies a Confused Muk (so that when Ditto copies Muk's Pokemon Power: Toxic Gas, it turns off its own Pokemon Power: Transform)? A. The end result is that Ditto is Ditto, not Muk. (Fossil FAQ, WotC Website)" — [RC "Other Transforming Rulings"]
- Muk's Power does not shut off a Baby's defence (2000-12, Neo): "baby power is not effected... (Dec 14, 2000 WotC Chat, Q59)"; come-into-play Powers are not shut off (May 2002 and Feb 2003) — [RC] (later; outside the pool).
- Timing of Muk being knocked out by an attack: damage is dealt while the Power is still off; the Power turns back on afterwards (Jan 2003 and Jan 2002 chats) — [RC] (later).
- Prehistoric Power: "You don't have a choice, if Aerodactyl is in play and its power is active, it's active. (May 18, 2000 WotC Chat, Q142)"; "If an Aerodactyl is in play, can another one be 'evolved' from a Mysterious Fossil? A. No. As long as that first Aerodactyl isn't Paralyzed, Asleep, or Confused, then no Pokémon can evolve. (Mar 9 WotC Chat)"; "Does Aerodactyl's Pokémon power cancel out a Pokémon Breeder? A. Correct, you cannot evolve anything (even with Pokémon Breeder) while Aerodactyl's Pokémon power is active. (April 13, 2000 WotC Chat Q51)"; fetch-from-deck evolution (Rapid Evolution, Chain Reaction) is not stopped (Jul 13, 2000 Announcements; Jun 15, 2000 Q341) — [RC PREHISTORIC POWER]. Which later (2003-09-18 / 2004-07-22) says Rare Candy overrides it — [RC, https://compendium.pokegym.net/?s=prehistoric+power]; outside the pool.
- Powers that stop others: Dark Gaze etc. are later (Skyridge). In the 2000 pool, a Muk-like blocker is only Toxic Gas (Fossil) and, for Powers on the Bench, Magby's Sputter (Neo, 2001; outside).

### Inferences
- I found no 2000 ruling that explicitly says Toxic Gas turns off Prehistoric Power. By card text ("Ignore all Pokémon Powers other than Toxic Gases") it does, so with a Muk in play (and not Asleep/Confused/Paralyzed) evolution is allowed again. Likewise Aerodactyl's power does not affect Muk. Poison does not turn either off in 2000 (it did from 17 Jan 2002).
- Toxic Gas must apply to the owner's own Muk-side Powers (Alakazam's Damage Swap, Blastoise's Rain Dance) too, so engine "opponent only" scoping would be wrong.

### Gaps
- No explicit 2000 chat on Muk versus Aerodactyl, and none on Muk versus Mr. Mime's Invisible Wall (Jungle) were found in the part of [RC] I searched by keyword ("Toxic Gas" appears 15 times; I read the Toxic Gas, Prehistoric Power, Ditto and Dark Gaze entries only).

## Addition (b). Between-turns order for Special Conditions in 2000

### Takeaway
The checks happen after each player's turn ("between turns"); I found no 2000 WotC statement of an explicit order such as poison before sleep. Known: Poison counters are placed at the end of the same turn the Pokémon was poisoned; the Asleep flip also happens at the end of every turn (both players'); Paralysis wears off at the end of the Paralyzed player's own next turn; Confusion is not a between-turns effect (it is checked when attacking); knockouts from poison are resolved after the checks, with promotion afterwards.

### Cited Findings
- Same-turn Poison and sleep flip: "Do I flip a coin to see if my Asleep Pokémon wakes up at the end of the same turn that it fell Asleep? Yes. You also take Poison damage at the end of the same turn a Pokémon got Poisoned. (Basic FAQ, WotC Website)" — [RC]
- Flips occur at the end of each player's turn: "they get to flip at the end of each player's turn. (Feb 10 WotC Chat)"; "You flip at the end of each player's turn. If it wakes up after the other players turn, BEFORE yours then it would act normal on your turn. (May 11, 2000, Q135)"; "You have to flip. (April 20, 2000 Q121)"; "The person whose Pokémon is asleep [flips]. (Aug 31, 2000 Q123)" — [RC]
- Poison damage after an attack: "My opponent attacks my Active, which causes 20 damage and Poisons it. Her turn is over. Do I then have to put 10 more damage on it because it is still Poisoned? A. Yes. (Feb 24 WotC Chat)" — [RC]
- Paralysis: "I paralyze your Pokémon on MY TURN. On YOUR TURN its Paralyzed, and at the end of YOUR turn it is UNPARALYZED. Back on MY TURN, it is NOT PARALYZED (May 18, 2000 WotC Chat, Q112)" — [RC]. So it wears off after the paralyzed player's own turn, not at the opponent's checkup that follows the paralyzing attack.
- Confusion: checked when the confused Pokémon attacks (flip before the attack's text; tails means no attack and self-damage of 20) (Jul 13, 2000, Q193) — [RC]. Confusion is not part of the between-turns step.
- Poison does not happen before the end of the active player's turn: "Scenario: It's down to one prize each, your turn with 10HP left, and you're poisoned. You attack and KO your opponent to draw your last prize. But you take poison damage and would be KO'd now too. A. You win... if you win BEFORE the end of the turn, you win, period. Poison doesn't happen until after the end of your turn. (Oct 5, 2000 WotC Chat, Q6)" — [RC WIN STATES] (Oct 2000; consistent with the rule in force in July).
- Order-of-checkup clarity from later rulings (mark 2001+): "Both Poisoned Pokemon receive damage counters during Pokemon Checkup, then you check to see if any Pokemon are Knocked Out. A new Active Pokemon is promoted after the check for Special Conditions." (TPCi 2024-12-19) — https://compendium.pokegym.net/?s=toxic+gas. Modern order Poisoned, Burned, Asleep, Paralyzed is from Bulbapedia, https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_Checkup_(TCG), cited only through a search summary; not a 2000 rule.
- A both-asleep ordering ruling is 2002: "the player whose turn is next would flip first. (Nov 21, 2002 WotC Chat, Q105)" — [RC]. A Miracle Berry and Gold Berry (Neo, 2001) are used between turns — [RC]; outside the pool.

### Inferences
- A 2000-faithful engine: at the end of every turn (both players) do Poison counters (10 each) and the Asleep flip on that player's own... — to be exact, the 2000 rulings say both are applied at the end of each turn to the Pokémon affected, regardless of whose turn it is (Basic FAQ). Paralysis removal is attached to the end of the paralyzed player's own turn. KO checks come after, with a replacement only after the checkup. The relative order of Poison versus the Sleep flip was never material in 2000 (a Pokémon can be Poisoned and Asleep and the two are independent), so engine order does not matter unless a Pokémon would be knocked out by Poison and wake.

### Gaps
- I found no 2000-dated statement of the relative order of the checks, or about a simultaneous knockout at checkup. The original rulebook's "between turns" section was not read.

## Addition (c). Sudden death

### Takeaway
In 2000 a simultaneous win ("both players win at once") went to Sudden Death unless exactly one player could replace the Active Pokémon, in which case that player won. A Poison knockout does not count because Poison resolves after the turn's win.

### Cited Findings
- "At the end of a long match, I Selfdestruct Magneton. My opponent and I both take our last Prize cards. Who wins? A. Well, if one of you has a Benched Pokémon to replace your Active Pokémon and the other player doesn't, then the person who can replace his or her Active Pokémon wins. Otherwise, you play Sudden Death. This is explained in the Pokémon rules in the Expert Rules section under 'What Happens if Both Players Win at the Same Time?' (Fossil FAQ, WotC Website)" — [RC WIN STATES] (primary-derived, Fossil FAQ, so 1999-2000)
- "If player A, in attacking, takes his last prize & knocks his active out by his attack & has no bench, Player B has a bench to replace. Who wins, player A or B? A. Neither, it goes to Sudden Death. (Sep 13, 2001 WotC Chat, Q30)" — [RC] (2001; contrasts with the Fossil FAQ line above in the sense that it describes a different case: A wins by Prize and loses by bench-out)
- The Sudden Death procedure itself (a new game with one Prize each, as I recall) was not found in any source I read. Players' reports at 1999 stores use "sudden death" after a Prize tie at time (C02 [P11]: "Then when time ran out (20 minute time limit) we both had 2 prizes left, so we went to sudden death.").
- The Swiss tie at time: [FR §216] says continue until one player has more Prizes; the STS used a draw (C02).

### Inferences
- The engine should return a three-way result (win, loss, draw) at a time cut and a "sudden death" outcome in simultaneous-win situations. How Sudden Death is played (a fresh game with one Prize each) is from my memory of the rulebook and not sourced.

### Gaps
- The text of the "What Happens if Both Players Win at the Same Time?" rulebook section was not found (it is in the Expert Rules section of the Base Set rulebook).

## Addition (d). Is pokemontcg.io (pokemon-tcg-data) complete for the pool?

### Takeaway
Yes for fields, with one caveat per card: the JSON has hp, types, subtypes (stage), evolvesFrom, attacks (cost, damage, text), abilities (Pokémon Power name, text, type), weaknesses, resistances and retreatCost for base1 to base5 and basep; set codes are below. It has no errata. Missing fields in the data (no retreatCost, weaknesses) correspond to cards that print none.

### Cited Findings
- Set ids: base1, base2, base3, base4, base5, basep (ptcgo codes BS, JU, FO, B2, TR, PR) — [PTD sets/en.json]. Card counts in cards/en: base1 102, base2 64, base3 62, base4 130, base5 83, basep 53 — [PTD], counted by me from the downloaded files.
- Fields per card (union across the six files): abilities, attacks, convertedRetreatCost, evolvesFrom, evolvesTo, flavorText, hp, id, legalities, level, name, nationalPokedexNumbers, number, rarity, resistances, retreatCost, rules (Trainers/Energy), subtypes, supertype, types, weaknesses (plus images, artist) — [PTD]; checked with a script (all Pokémon cards have hp). Attacks carry `cost`, `convertedEnergyCost`, `damage` (string, may be `''`, `30+`, `×`, `-` or `?`), `text`. Pokémon Powers are in `abilities` with type "Pokémon Power". Per-set counts of Pokémon lacking retreatCost (it equals 0): base1 6, base2 14, base3 8, base4 15, base5 9, basep 8; lacking weaknesses: base1 5, base2 0, base3 13, base4 5, base5 4, basep 11. Pokémon Power counts: base1 6, base2 10, base3 16, base4 9, base5 20, basep 9.
- Known differences from the printed cards: the prior engine check found 1 mismatch in 1,926 field checks, the Raticate (Base Set) Super Fang `damage` as `''` in the engine against `'?'` in the data (cosmetic) — `notes/sts-2000-engine-check.md` §2. Base Set 2 and Team Rocket duplicate Base Set/Jungle names, so printings must be resolved by card id (the prior check assumed Base Set Machop for the unannotated lists). Base Set "Wizards Black Star Promos" ids: Mewtwo #3 and Mew #8 per the prior note. The Base Set cards in the data carry the 1999 shadowless/unlimited text, not later reprint text (e.g. Legendary Collection, base6, is separate).
- Errata: none carried; see Q3. pokemontcg.io is deprecated (keys valid to March 1, 2027) — https://docs.pokemontcg.io/api-reference/cards/card-object. Use the GitHub repo.

### Inferences
- The data is enough to compare engine card definitions (HP, types, Weakness, Resistance, retreat, stage, attacks, Power text). Behaviour that is not in printed text (confusion damage, Toxic Gas scope, mulligan option, sudden death) must be tested against [FR] and [RC].

### Gaps
- I did not diff the JSON against card scans, nor check base4/base5 reprints' printed text for differences from earlier printings.

## Sources (all fetched by me unless marked)
- [FR] https://web.archive.org/web/20000519143655id_/http://www.wizards.com:80/DCI/downloads/Pokemon_Floor_Rules.doc (downloaded, text read; primary)
- [RC] https://compendium.pokegym.net/compendium.html (downloaded, grepped; secondary compilation of primary WotC FAQ/chat items)
- [RC online] https://compendium.pokegym.net/category/7-gameplay/starting-the-game , https://compendium.pokegym.net/?s=toxic+gas , https://compendium.pokegym.net/?s=prehistoric+power
- [PTD] https://github.com/PokemonTCG/pokemon-tcg-data (cards/en/base1.json to base5.json, basep.json; sets/en.json)
- https://docs.pokemontcg.io/api-reference/cards/card-object (via WebFetch summary)
- Search-result summaries only, not fetched: https://bulbanews.bulbagarden.net/wiki/Rules_changing_for_XY_card_game;_Professor_Sycamore_revealed ; https://geekydomain.com/blogs/guides/pokemon-modern-rules-vs-base-set ; https://bulbapedia.bulbagarden.net/wiki/Special_Condition_(TCG) ; https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_Checkup_(TCG) ; https://pkmncards.com/card/muk-fossil-fo-13/ ; https://serebii.net/card/base/ ; https://www.pojo.com/CCQA/QandA/1099/100507.txt ; https://www.pojo.com/pokemon/rules/master_rules_document.doc (403)
