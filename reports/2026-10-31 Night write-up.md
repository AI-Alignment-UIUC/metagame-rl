# Night write-up, 2026-10-29 to 10-31 (C121-C143, log #550-#649)

## Ground truth: not moved

- **Shape:** the gated drafting base sits 11.2 ± 3.8 from the lists' 13.5 / 28 / 18 over 13 seeds (#587). Its best single seeds
  (7.4, C120 s7; 5.9, C124 s13) are draws: continued seeds drift back to about 13 (#578).
- **Tempo cards** (PlusPower, Gust, Item Finder, Scoop Up): 2.0 ± 0.4 copies a deck (#587), against 9.2 in the lists, and 2.7
  in the random decks drafting starts from (#581). Drafting wears them down; it never adds them.
- No lever beat noise on either readout.

## What was ruled out, and how

**Drafting levers (none moved the decks)**
1. A per-turn discount in the loop's pilot (C121): tempo cards 2.56 over four seeds; the replicating pair alone was only +0.27
   (about 0.9 SE), so no effect (#567-568).
2. Longer drafting (C123, C125): shape doesn't settle. A near seed went 6.9 → 13.4 and a far one 17.4 → 13.6 (#562, #578).
3. A stronger discount (C124): null, tempo cards 2.13 (#574). More draft-head entropy (C126): the setting didn't change
   exploration (#573, #576).
4. Selection itself, in all 18 seeds: it trims Trainers (−0.23 a move, SE 0.02) and keeps Energy (+0.37, SE 0.02) against
   the head's proposals (#564).
5. The per-card ledger (C127): selection trims the tempo four (−0.072 a move, SE 0.029), and the head adds them as often as
   it removes them (#580).
6. The Prize margin in selection's score (C128): no change (Δ +0.008, SE 0.039) (#583).

**Paying for speed (games didn't get faster)**

7. A win paid more the sooner it comes (C130): time endings 45% against the controls' 41% (#594).
8. Lower clock payouts in training (C131): time endings 39%. Its ledger hint (z 1.8) didn't replicate (C131b, Δ +0.028,
   #595, #599).

**The pilot**

9. Search against a passive opponent (C132, C132b): one or two turns of lookahead leave pace within 1-2 turns of greedy
   (#601, #604).
10. The policy's blind spot (C133): it gives PlusPower and Item Finder about zero probability at exactly the moments a fast
    line plays them (528 of 528 and 190 of 192 outside its top 3) (#606).
11. The field (C134): our games offer PlusPower and Gust as many knockout chances as the human field (0.90 of it, 1.00 on
    cleanly logged attacks) (#610).
12. The value (C135): the pilot's own value already credits the play. Its search plays PlusPower at 83% of 10-HP
    breakpoints (greedy 0.4%) and takes 55% more Prizes a turn (#613).
13. Teaching the policy that search (C137): it fails at both margins. The policy spreads out (entropy +0.27) and can't follow
    the targets. That's the fourth failure of this kind (#621-623).
14. Search inside the loop (C138): with the same pilot on both seats, games aren't faster (time endings 33-36% against 34%),
    so C135's gain was one seat against a greedy one (#628-630).

**What PlusPower is worth** (event points; 0 = an Energy)

15. Head to head (C136): 0.44 greedy, 0.50 with search on both sides (#616).
16. Against the human field (C139): −0.054 greedy (SE 0.011), −0.003 with search (SE 0.014) (#632).
17. With a longer clock or none (C140): −0.028 (0.018) and −0.044 (0.021). The clock isn't the cap (#636).
18. With search scored by Prizes, not the value (C141): +0.011 (0.014). The value isn't the cap (#637).
19. As a package of all four tempo cards (C142): −0.037 (0.008). Its gain over the sum of singles is confounded with
    surplus Energy (#641-643).
20. Across pilot strength (C143): a far stronger greedy pilot prices it the same (−0.055 against −0.054). Deeper lookahead
    wasn't a stronger player (win share 0.52, SE 0.03) (#648-649).

## Still open

- The human lists run about 2.75 PlusPower a deck, yet every player we can build prices it at an Energy or a bit less. By the
  ground-truth rule something in our setting is still wrong. Cheap checks are exhausted for PlusPower: field, clock, scorer,
  unit, engine code and reference lists are all clean (#608, #643).
- Untested: a much stronger player (a large build, now a weak prior), and the lists' other Trainer groups under search (next).

## Corrections made along the way

- **#584 → #588:** I wrote that two-seed bands understate seed noise; C129 showed the opposite.
- **#607:** "9 against 19-32 own turns" compared a best case with a metric that skipped the commonest win. On any win the
  pilot is about 3 turns slower than the script, and the script decks out in 29% of games.
- **#642:** a small SE correction in C142's readout.
- **#649:** C143's strength gate used a score that isn't constant-sum in a mirror, so it could never pass. Head-to-head gates
  now use win share.
