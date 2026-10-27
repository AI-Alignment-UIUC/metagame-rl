# Research session handover (2026-10-27 04:09 by `date`; replaces 10-26 23:31's)

**Trigger (Evan rows 56, 79-81).** A deep round fires only on a line in `notes/audits.md` that starts
`RESEARCH CALL:`, the auditor's own judgment that the work is not moving the metrics.
- At least 3 hours between rounds; the last round was round 2 at 10-26 21:16. A topic not researched before.
- There are 2 calls so far. Line 563 (A44) was answered by round 2. Line 616 (A54) was answered by #292 without a deep
  round, and A68 closed it.
- The watchers were reaped at about 03:25 (low memory; Claude Code says not to restart them unasked). The other
  agents message this session on results.

**Topics already researched** (don't repeat): see the folders under research_notes/. They cover the keep bar and
noise, card sub-decisions, self-play drift, return decomposition, oracle critics, intrinsic signals, chains, entity
pointers, tokenization, action-dependent baselines, LOCM and Showdown targets, Muesli, CMPO and MPO, per-card draft
attribution, and Dominion and Slay the Spire draw engines. Unresearched candidate: selection under noisy fitness
(threshold selection, racing).

**State after the night (log #292-#304):**
- Prompt-answer work stopped. C88 lost M; C89 is R-small, powered, with no answer gain (#294, #296).
- C91 is R-repro: two-seed G1 6.43 with the gate restored (#302-#303). The anchor is valid on engine K.
- C90, seed 1 against C85: between (G3 0.219 against 0.114; #299-#300). Seed 2: C90-s2 G3 0.1578 and G1 8.47. C85-s2
  ends about 04:35. Read both by Amendment 3: a G3 gain needs both seeds' C90 - C85 differences >= +0.08; R-pilot's
  Trainer leg needs a fall in both G3's 12 and the population.
- C92 is R-population (#312-#313): the 479 pilot on fresh decks matches C90. C91's shape lives in the 479 decks and
  head.
- C90 two seeds: null on G3 (#308-#309).
- **C93 is R-gate (#316), the first replicated G1 effect.** The gated draft from fresh decks sits 7.6 closer to the
  lists over 4 seeds (Welch CI [−11.9, −3.3]). G3 and Energy are unchanged.
- The rediscovery sizing (#314-#315): the lineage first came near at 290, ungated. The step from 13 to 6 at 290
  coincides with the deckcross adoption, a possible judge artifact.
- Open for Evan (via 333-10):
  1. the gate as default for fresh screens (§10);
  2. the 289/290 judge check;
  3. a gated fork at 290 or 240;
  4. the draft's reward, since Energy stays high.
- Updated 2026-10-27 07:18.

**Rules.**
- Log entries: check the last number and append in the same step.
- Times: substitute `date` into the text (placeholder plus sed); never type a guessed time. Three guessed times were
  fixed tonight.
- Name the deck set behind every shape number: G3's 12, G1's top 12 by z, or the population (#300).
- Usage: 5h 19% / week 81% at 00:57. No subagents spawned this session.
