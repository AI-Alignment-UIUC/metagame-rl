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
- **Round 3** (Evan about 07:25, done 08:45; `research_notes/Value heads over prompt answers/`, log #319):
  - C95 has 8 value-head candidates scored offline on the C94 oracle.
  - C96 is A79's search check of M, running ahead of C95's B set.
  - Read both against their records. Under Evan's row 87, rounds may follow any call with at least 1 hour between
    them, and each must end with a queued run that has a record and bands.

**Rules.**
- Log entries: check the last number and append in the same step.
- Times: substitute `date` into the text (placeholder plus sed); never type a guessed time. Three guessed times were
  fixed tonight.
- Name the deck set behind every shape number: G3's 12, G1's top 12 by z, or the population (#300).
- **All outside research goes through the deep-research skill** (Evan about 10:15: "the scholar should be using the
  deep research function"; addendum "when it does research at all"). That covers every round and every literature
  or web lookup, through `anthropic-skills:deep-research`, never lean-readers. Reading the repo's own files and logs
  isn't research; do it directly. Read usage first. The report goes to
  research_notes/<topic>/, and the round ends in a queued 30-minute run with a record and bands (rows 87-88).
- Card identity and full-deck targeting (Evan rows 89-90) is 333-10's workflow. Don't repeat it. Turn its
  report's top proposal and its minimal variant into 30-minute records.
- **Evan 14:03 (via 333-10): "Keep experimenting for awhile, don't wait on my approval right now."** Until he says
  otherwise, approval isn't a gate. P4's longer version runs on its mechanism pass. If P2, P1 and P4 leave Item Finder
  and Computer Search unmoved, write the turn-level planning record (row 99) and hand it to implementation. Propose and
  queue the next runs from the results. The standing rules all stay: bench focus, per-card goal, quarantine, bands
  first, the null rule, 30-minute stages with stop rules, deep-research for research. Coordinator calls go to 333-10.
- **Bench state (14:0x):** arm 0 (C100) is done, stronger at play with flat prices. C99 on the bench is between, with
  timing adding nothing. P2 s1 is R-dead by the letter with live logit readouts; s2 reruns about 14:15-14:55. P1 runs
  as built, with the two-Trainer gate missed. P4 is recorded. Records are under runs/probe/BENCH/.
- **Research cadence now (333-10, about 17:45, for the weekly pace; the week was at 22% about 9 hours after its
  reset):** a deep-research round only on a research call, or at most every 2 hours. Smallest breadth. Skip while
  the 5-hour window is over 60%. This holds until 333-10 says otherwise.
- **Previously, hourly deep research** (Evan about 14:05). The skill runs at its smallest breadth: at most about 3
  subagents and short reports. Skip the round, and log the skip, when the 5-hour window is over 60% (333-10's usage call after
  A91). A research call takes that hour's topic. The timer is a one-shot background sleep of 3600 s, re-armed after
  each round.
- **Week rule (working rule 18; auditor, 14:2x).** While the week's use is ahead of the share of the week elapsed
  (about 17% used against 4.6% at 17:10, for about 1.5 days at today's pace), each round uses one researcher plus the
  report writer, even after the 5-hour reset. This holds until Evan says otherwise.
- Cite a log number only after the append prints it. Twice on 10-27 a message or record named the number before the
  append, and other agents' entries had shifted it.
- Usage: 5h 19% / week 81% at 00:57. No subagents spawned this session.

- **Usage reading (333-10, 2026-10-28 00:04):** `~/.claude/usage-latest.json` has several writers and flips; always use the HIGHER week and 5-hour reading seen across writers. Week was 29% at about 15 h after reset (about 2%/h against about 0.5%/h sustainable), so deep rounds run only on a RESEARCH CALL or at most every 2 h, smallest breadth, skipped while the 5-hour window is over 60%.

## State at 2026-10-28 15:03 (research session)
- **Cadence (333-10, 15:01):** week 39% at about 18% elapsed. No deep-research rounds on a timer. Answer an auditor
  RESEARCH CALL from existing notes at the smallest breadth. The 2-hour timer is stopped.
- **Held:** a design round on draw-to-tempo credit (how a pilot learns to turn drawn cards into the plays they enable).
  It runs only if Evan picks it or usage gets back under the line. 333-10 is taking it against (b), resuming drafting,
  to Evan.
- **Today's chain (log #493-#533):**
  - The engine is right (audit, flow checks), and the decks can be fast (C115b: 9 own turns when the line comes
    together).
  - Pilots under-play speed Trainers (Oak and Bill held 79-96%, PlusPower about 0, a short bench).
  - Holding is right under their own continuations (C116), and stays so in faster games (C117, invalid, not banded).
  - P9 (a per-turn discount) and P10 (forced Trainer exploration) both read between or no effect. Both cut deck-outs
    and retreats in the mirrors.
- **Records written, not run:** P9b, P7, C109b (withdrawn), C112 (skipped: needs a build).
- **References:** `reports/STS 2000 rules and card references.md` (35-item checklist);
  `notes/data/cards/printed_reference.json` (#487); `reports/Bench summary 2026-10-28.md` (corrected wording);
  `reports/2000 game pace sources.md` (thin: pojo 403, Wayback denied and not retried).
- **Held for Evan (auditor A120, 2026-10-28):** C118, Oak priced with a search (oracle-style) continuation against the pilot's own (`runs/probe/C118-conversion/record.md`); the hand-off was retracted for usage.
