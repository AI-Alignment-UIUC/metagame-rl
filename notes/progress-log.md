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
