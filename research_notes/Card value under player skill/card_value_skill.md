# Card value under player skill

Tags: [read] = page fetched and quoted; [snippet] = search-result text only, not opened; [memory] = my background knowledge, not checked this session. Coverage is thin: about 15 tool calls, several sources blocked or PDF-unreadable. Gaps are listed in each section.

## 1. Skill-dependence of card value

### Takeaway
Public TCG analytics measure win rate by skill tier mostly at the deck or archetype level, not per card. The one clear per-tier number I found is a deck-level gap (HSReplay, Face Hunter: 48.8% at Diamond vs 56.6% at Bronze). Per-card skill brackets for MTG and Hearthstone were not found. The qualitative sources say skill matters most for high-ceiling, multi-step and flexible-deck cards, but none quantify it per card.

### Cited Findings
- 17Lands GIH WR counts a game when the card was in hand, whether opened or drawn, and the card need not be cast. [read] — https://mtgazone.com/17lands-in-defense-of-the-data/
- The same author says GIH WR "still does bias towards cards which are in more controlling decks" because longer games show more cards. [read] — https://mtgazone.com/17lands-in-defense-of-the-data/
- The author says OH WR favors cheaper and aggressive cards, and calls ALSA one of the least biased stats because it reflects how others pick. [read] — https://mtgazone.com/17lands-in-defense-of-the-data/
- Draft pods are the first 8 players to queue, so they mix player strengths; the author calls skill "the biggest place where your skill as a player matters when it comes to overriding the data." [read] — https://mtgazone.com/17lands-in-defense-of-the-data/
- 17Lands tiers players top/middle/bottom, and the card-ratings API exposes a user_group filter. [snippet] — search result for "17lands games in hand win rate player skill bracket"; the 17Lands docs were not opened.
- One analysis reported top-tier players at 60.7% and middle-tier at 57.1% in best-of-one games, and estimated a card-level tier gap of about 10 points. [snippet only; the source article was not identified or opened, so treat as unverified]. The same search surfaced a claim that the pool is less competitive than Diamond; also unverified.
- HSReplay's 2020 rank-rework FAQ: All Ranks data is "polluted by the large volume of low rank data." Face Hunter win rates: 48.8% Diamond, 56.6% Bronze, 54.4% All Ranks; the FAQ warns a Diamond player using All Ranks would think a sub-optimal deck is fine. [read] — https://articles.hsreplay.net/2020/04/07/rank-rework-faq/
- The same FAQ says the per-card picture is not discussed. [read] — same URL.
- Forum definitions, not an official source: skill cap is "the extent to which piloting skill effects the winrate results of a particular deck archetype"; skill ceiling is "the difference to the median winrate a good player can achieve with a deck." [read] — https://us.forums.blizzard.com/en/hearthstone/t/question-understanding-skill-cap/82841
- The same forum thread says skill cap rises with decision complexity, deck flexibility, and the number of actions. It names no specific card type. [read] — same URL.
- StarCityGames floor/ceiling framework: "High ceiling cards are often used to give a deck another gear when both players have a strong draw." Floor is "what it does with no help from other cards." [read] — https://articles.starcitygames.com/articles/a-three-pronged-approach-to-card-evaluations/
- The same article notes that a card's win rate can reflect its archetype rather than the card; the article itself does not discuss win rates. [read for the framework; the archetype point is a snippet from the search summary].

### Inferences
- The deck-level HSReplay gap (about 8 points between Bronze and Diamond for the same deck) is the largest skill effect in the sources I read. Card-level effects are probably smaller or hidden inside it, but nothing I read measures this.
- Per the forum and SCG framing, the skill-sensitive cards are high-ceiling ones: they depend on the turn, the board, and the opponent's draw. Their measured value is conditional on how well the pilot finds the right turn.
- The 17Lands "in hand" metric and the HSReplay per-rank view both mix players of different skill, so a card's measured value is weighted by the population's skill.

### Gaps
- No per-card GIH WR by top/middle/bottom bracket was retrieved. The 17Lands API doc and card-ratings page were not opened.
- No HSReplay per-card-by-rank table was found; the search returned card pages, which were not fetched.
- No MTG "skill-testing card" analysis was found. The search surfaced only general Limited articles.

## 2. Measurement validity

### Takeaway
I found no Hearthstone or MTG paper that values a card by swapping it for a basic resource and playing the swapped deck. The closest material is a deck-recommendation paper whose methods I could not read, and an econometric thesis that values cards by price. The biases below are standard reasoning from the sources, not findings from the card-game literature.

### Cited Findings
- Q-DeckRec (arXiv 1806.09771) learns a deck search policy and reports that it builds "winning-effective decks" with less compute than baselines. [read: abstract only] — https://arxiv.org/abs/1806.09771
- The Q-DeckRec abstract does not say how many games each win rate uses, what opponent it plays, or whether any card-level value is measured. The PDF was unreadable through WebFetch. [read] — same URL; PDF fetch failed.
- Karaffa (Charles University thesis) estimates Hearthstone card "game value" from attributes and compares it with market price, using econometrics and an ordered choice model. [snippet] — https://vskp.vse.cz/english/57220 (full text not opened)
- Shapley value: a card's contribution is averaged over the orders in which players join, and Shapley values sum to the total value, so they avoid double counting. [snippet; generic Shapley sources, not card-game]

### Inferences (standard reasoning, not sourced findings)
- **Same pilot on both sides.** The swap compares a deck with the card against a deck with an Energy in its place, with the same policy playing both. That value holds only for that policy's skill. A weak pilot undervalues cards that need precise timing, so a low measured value is what a weak pilot should produce; it does not show the human lists are wrong.
- **Interaction effects.** A card's value depends on the other 59 cards and on the opponent's deck. A single swap in one fixed deck is one point in that space. Averaging over decks (for example a Shapley-style average over sampled decks) reduces this, but needs many runs.
- **Selection effects.** Human lists are built by players who choose the cards; a card with 2-4 copies is chosen because players draw it and find it useful in their own play. The lists reflect player skill, not just the card.
- **Diminishing returns on the replacement.** If the deck is already Energy-heavy, one more Energy adds little, so the baseline is low and a trainer will look worth about one Energy. The swap result depends on the Energy count in the baseline. Measure with the baseline Energy count varied.
- **Win rate when drawn (GIH-style)** is correlational. It counts games where the card was in hand but never played, and it favors controlling decks (see Section 1, 17Lands note). A swap test avoids that bias but adds the pilot-skill dependence above.

### Gaps
- No paired-swap, counterfactual or Shapley card-value study in Hearthstone or MTG was found. Two searches returned only general methods, plus the Karaffa thesis.
- LOCM and IEEE CoG/AIIDE deckbuilding papers were not searched (budget).

## 3. Beyond-one-turn play and the case for tempo cards

### Takeaway
The only retro-format sources I could reach are a 2000 strategy article (seen in a search snippet only) and a card-text page. Neither makes a quantified case for a tempo card beating an extra basic resource.

### Cited Findings
- Pojo.com "Energy Removal" (July 2000): the search summary says the strategy is "still very good," but notes the Energy Removal Pokémon are evolutions and "kind of slow" compared with a haymaker. [snippet] — https://www.pojo.com/TCGStrategies/July2000/14o.htm. Pojo returned 403 in an earlier round and was not fetched here; treat this as unverified.
- Bulbapedia's Energy Removal page reportedly notes the card was "deemed too powerful" and replaced by Energy Removal 2. [snippet, not fetched]. Bulbapedia returned 403 in an earlier round, so this is unverified.
- A Spanish WikiDex page advises using Energy Removal on a benched Pokémon that the opponent is building up. [snippet] — https://www.wikidex.net/wiki/Energy_Removal_2_(TCG) (this URL from search; not opened)
- Dittobase card page for Energy Removal (Base Set 2, 119): card text "Choose 1 Energy card attached to 1 of your opponent's Pokémon and discard it." It has no strategy text. [read] — https://www.dittobase.com/tcg/cards/base-set-2/119-energy-removal
- A Pokémon TCG Pocket guide argues energy should be attached "with a purpose" and the bench prepared for a replacement attacker. [snippet] — Pocket, not the physical game; promotional; low weight.
- Floor/ceiling: high-ceiling cards give "another gear when both players have a strong draw." [read] — SCG link above. This is the closest source for holding a tempo card for the right turn.

### Inferences
- The retro guides make the tempo case qualitatively: a removal effect is worth more when it targets a specific investment (a bench Pokémon being built up, or a race). An Energy in the same slot does not do this. That argues a swap test understates such cards if the pilot does not time them.
- The argument is not quantified in any source I read, so no comparison to an Energy can be drawn from these.

### Gaps
- No retro-format article on bench setup or multi-turn denial was retrieved with full text. The useful 2000-era content I could reach was a search snippet.
- No source quantifies a tempo card's value against an extra basic resource.

## 4. Game-AI methods for skill-intensive cards (not searched)

Budget did not allow a search on this. Known directions from memory, unverified here: stronger reference agents, skill-stratified evaluation (run the same deck at several pilot strengths and check whether the card's value moves), and opponent modeling. The skill-stratified option is the one that answers the project's question most directly. [memory]

## Summary for the project
- No public source I read gives a per-card skill bracket, so the claim that a card's value rises with skill is supported at the deck level (HSReplay) and by qualitative analysis (SCG, forum), not by per-card numbers.
- Plausible reading, flagged as inference: a swap test with a fixed mid-skill pilot measures a card's value at that pilot's skill. A low value for tempo trainers is consistent with a pilot that does not time them. Checking this needs the same swap at several pilot strengths and with the Energy count varied. The human lists are ground truth for the outcome, but the swap cannot show by itself that a human-level pilot would value the card higher.
- Gaps to close before relying on this: 17Lands per-bracket card tables, HSReplay per-card-by-rank, the Q-DeckRec full text, and LOCM/IEEE CoG card-value papers.
