# Progress log

Append-only. One entry per finished todo, newest at the bottom. Entries are never edited or
deleted afterwards; a correction is a new entry that says what it corrects. The README status is
summarized from this log (see `CLAUDE.md`).

Entry format:

```
### #N · YYYY-MM-DD · <plan item, e.g. A1.2> · <todo in a few words>
- **Done:** what changed, with paths, commits or the submodule pin.
- **Evidence:** tests run and their results, numbers measured, or "not verified".
- **Found:** anything learned along the way: bugs, surprises, open questions. Omit if nothing.
- **Next:** what this makes possible or points to next.
```

---

### #1 · 2026-10-04 · A0 · Engine covers the 2000 STS field (backfilled)
- **Done:** On the fork's `sts-2000-pool` branch: Fossil Ditto re-enabled with its two open TODOs
  closed (copying passive Pokémon Powers, offering copied in-play Powers), and a new Wizards
  Black Star Promos set with Mewtwo #3 and Mew #8. Report in `notes/sts-2000-engine-check.md`.
- **Evidence:** 24/24 archived lists build and start a game; 541 engine specs pass (25 new);
  68/68 interaction tests; 1,926 card-data checks with 1 cosmetic mismatch; 22/23 rulings.
  ~9 games/s per core, near-linear to 8 workers; seat A won 54.5% ± 5.8 over 288 mirror games.
- **Found:** Rulings test T18 (Mysterious Fossil as a starting Basic) fails; not in this field.
  SimpleBot costs ~30× the engine per move, so it's an evaluation floor only. Two throughput
  fixes (log cloning, `propagateEffect` card-order cache) measured 540 → 98 µs/action in a
  scratch test but are not committed.
- **Next:** A1, starting with committing the throughput fixes.

### #2 · 2026-10-05 · Housekeeping · Progress log and recursive status
- **Done:** Added this log, a `## Status` section in `README.md`, and the update rules in
  `CLAUDE.md`, following Wu et al. 2021 (recursive summarization).
- **Evidence:** Not applicable (documentation only).
- **Next:** A1.1.

### #3 · 2026-10-05 · A1.1 · Commit the throughput fixes
- **Done:** Fork commit `888b385`: `Store.reduce` keeps existing log entries by reference instead
  of deep-cloning them into the rollback backup; `propagateEffect` replaces the per-effect sort
  with precomputed ranks (rebuilt when an unseen card appears) and bucketing. New
  `packages/common/src/store/store.spec.ts` (7 specs). Folded in `notes/scripts/ryuu_engine_equivalence.js`
  (differential test, old vs new Store) and fixed its illegal-retreat generator, which used bench
  slot 4 (a real slot), so 18 "illegal" retreats were legal and accepted by both engines.
- **Evidence:** common 250/250 specs, sets 684/684. Equivalence, 300 seeded SimpleBot games:
  state identical after every one of 41,381 actions, 3,651,418 card-order checks equal; after
  the generator fix, 40 games at 30% injection rejected 3,922/3,922 illegal actions with no
  value change. `ryuu_selfplay.js --nopolicy --games 300 --seeded`, same machine:
  554 → 160 µs/action, 18.7 → 64.6 games/s/core (3.5×).
- **Found:** The scratch estimate (98 µs, 5.4×) was optimistic; it skipped the logs entirely and
  keyed the cache on array length. Rejected illegal actions still change which arrays are
  shared (deepClone doesn't preserve sharing), identically in old and new engines; values are
  unaffected. Where the remaining 160 µs/action goes is not profiled yet.
- **Next:** A1.2 legal-action enumerator. The A1 exit target (≥ 50 games/s/core) is met by the
  engine alone, so the enumerator and encoder have ~25% headroom; profile again after them.

### #4 · 2026-10-05 · A5.3 prep · Fold in the Black Star Promos
- **Done:** Fork commit `64330a4`: 12 promo cards (Pikachu #1/#4, Electabuzz #2, Dragonite #5,
  Arcanine #6, Jigglypuff #7, Meowth #10, Eevee #11, Mewtwo #12, Venusaur #13, Cool Porygon #15,
  Computer Error #16) with specs, registered in `init.js`; #9 and #14 are reprints. Folded in
  the matching script changes: promo set in the rulings and throughput scripts, card-number
  matching in `ryuu_card_data_check.py`, `--flag` handling in `ryuu_harness.js`, and the new
  `ryuu_promo_fuzz.js`.
- **Evidence:** 143 new specs pass (in the 684). Card-data check: 2,025 field checks, 12 matched
  by card number, 1 known cosmetic mismatch (Raticate Super Fang). `ryuu_promo_fuzz.js --games
  400`: 400/400 finished, 0 stuck, 0 cap, 0 errors; every promo attack, Power and Trainer used.
- **Found:** Mew's Devolution Beam came up only 2 times and Texture Magic 4 times in 400 games;
  they rely on specs more than play.
- **Next:** Back to A1.2.
