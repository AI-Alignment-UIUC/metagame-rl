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
- **Deep-research cadence (Evan, 2026-10-28 about 23:55, row 111, relayed by 333-10):** "deep research max every 3 hours". At most one round per 3 hours, through the skill. Only on a RESEARCH CALL or when no written lever is left; skip while the 5-hour window is over 75%; smallest breadth; each round ends in queued, banded screens. The auditor runs every 4 hours.
- **Queued idea (auditor A133, 2026-10-30, a note, not a call):** after C121's 4-seed read, record a CPU check of each focus card's marginal value as the draft's own selection signal scores it at the C120 base population. If it is about 0 within noise, pilot levers can't reach the lists from here, and the route is a stronger selection signal.

## State at 2026-10-30 01:01 (research session d5a94144)
- **A133's CPU check is answered from the logs (log #564), so don't run it.** `select_lean.py` over all 18 engine-K
  seeds: selection's accepted minus proposed is Trainers −0.23 a move (SE 0.02) and Energy +0.37 (SE 0.02), with the same
  sign in every seed, gated or not, with or without the discount. A stronger selection signal would sharpen the push
  away from the lists. The per-card version isn't in the logs.
- **Next deep-round topic, when one is allowed:** pace and endings are already well covered (#505-#536, `2000 game pace
  sources`). Before picking a topic, check those and the README's "Where things stand". Still unresearched: selection
  under noisy fitness (now low value, given #564).
- **Watcher:** a background sh poll of `^RESEARCH CALL:` in notes/audits.md (baseline 21 lines), with a 90-minute fallback.
  The script is in this session's scratchpad.
- **Peers:** the names don't resolve. Implementation is `uds:\.\pipe\LOCAL\cc-msg-c683246c0478ea2d3569ebb68f85728b`; two
  other pipes (124079…, 743f67…) got #564 too. This session is 5a54a0….
- **Usage at 00:54:** 5h 28% / week 58% (38% of the week elapsed; reset 2026-11-03 08:00 CST). Ahead of the line, so no
  fan-outs. No subagents spawned.
- **01:17:** every record needs a **Kill** line (`loop.py launch` refuses one without it, §10). C125 and C126 lacked it,
  and implementation added C121's line at 01:16 (#568). C121 meets #561's queue gate (4-seed T4 2.562), but the
  replication pair alone is +0.27, about 0.9 SE, so it isn't a claimed effect. C126 s14 runs; C125 follows C124's γ.
- **02:27:** C124 reads R-null (#574; s13 G1 5.87 with T4 1.75). C125 runs with γ 0.98 (C121 s8, s9). C126's β didn't move
  the head's dials (#573). Wrote **C127**, the per-card selection ledger at seeds 16 and 17 (#575), and handed it off.
  The watcher was re-armed at 02:3x after its 02:25 fallback (no call).
- **02:52:** C127 s16's ledger passes integrity on its real rows (iterations 0-4, 0 mismatches). Interim, one seed, 5
  iterations, not a result: T4 λ −0.15 (SE 0.09), T4 share of proposed copies 3.9% (149 copies; the 50-copy power floor
  will be cleared easily). Basic Energy is 19.1% of proposals. Read at 29 by the bands only.
- **02:55:** C125 stage 1 (#578): s9 R-worse (6.93 → 13.43), s8 17.37 → 13.60. Research asked implementation to stop s8's
  stage 2 (the band is settled, and it competes with C127). Lesson: a seed's G1 at 29 regresses toward the base mean
  (about 13), so near-list endpoints are draws, not recipe effects. Next record after C127's read (about 03:45):
  R-proposal leads to a base-measure mix (Nf with a uniform share, a small build, the G1 watch on); R-selection points
  to the pilot or judge, whose bench levers were all small, so a deep round is warranted once usage allows.
  Usage at 02:55: 5h 7% / week 59% (line about 58.7%, from 58% at 00:54 to 92% at reset), so no deep round yet.
- **03:0x, the R-proposal branch is dropped before writing.** `--draft-base-ent` (never varied from 3.0) flattens Nf toward
  uniform. Uniform gives T4 4/277 = 1.4% of proposed copies, and Pokémon 225/277; Nf already gives T4 3.9% (s16
  interim). So raising it would cut T4 and court the Pokémon slide. Crude arithmetic, to be confirmed at C127's read: if
  selection were neutral, decks would carry about the incoming share, 3.9% × 60 ≈ 2.3 T4 copies, about the observed
  2.07. Reaching 9.17 needs about a 15% incoming share or a clearly positive selection lean. Both come from the loop's own
  game results (the head's REINFORCE and the paired selection), so either branch leads back to how the games price T4.
  No prior-free proposal fix exists (a supertype-balanced base gives T4 only about 3%).
- **03:45:** C127 reads R-selection plus proposal-side starvation (#580). Research's addition (#581): wide decks start at T4
  2.67 and Trainers 28 (the lists' count), so drafting erodes both, and the "T4 lifts" are less erosion. Wrote **C128**
  (the Prize margin in selection's paired score, W 0.5, Evan's 10-12 reward; seeds 18 and 19; C127 is its control) and
  handed it off. If R-reverse or R-null, the next step is a deep round on the play regime once the week is under its line.
- **04:47:** C128 reads R-null (#583). C129 is calibration (two W 0 ledger seeds, the between-seed noise; #584-585, readout
  about 05:45). **RESEARCH CALL A135** (04:44) was answered from notes in #586 with no run: every stronger player prices the
  lists' Trainers at or below an Energy, and all share the slow pace. **The held deep round's topic is how a self-play pilot
  learns tempo** (passivity and stalling in self-play card or board-game agents, with remedies beyond P9's discount and
  P10's forced exploration). Check that research_notes/ hasn't covered it first. It runs when the week is under its
  line. The watcher is re-armed with a baseline of 22 lines.
- **10:12: deep round 4 done** (A136, launched 10:06 at 5h 3% / week 61%; one Haiku researcher plus a Sonnet writer). Report:
  `reports/Self-play tempo learning methods.md` (evidence thin; no documented stall-and-fix case). **C130** (win-speed
  payout, losses untouched; seeds 22 and 23) is recorded and handed off (#590). Proposal 2 (lower clock payouts in
  training) is next if C130's pace is null. The next deep round is no earlier than 13:06. Unread lead: Xi et al., arXiv
  2303.04096 (LOCM, smooth fictitious play).
- **11:08:** C130 reads Harm (s22's watch) and is null on pace (#594: s23's time endings 45.4% against 41.3%, steps 104.8), so
  the line ends. C131 (clock payouts) s24 and s25 read at about 12:05. If C131 is also null, check whether 30 drafting
  iterations of PPO can move the pilot's pace at all, before another reward lever. P9 on the bench (pilot-only training)
  moved knockouts per own turn 1.13×, and the loop's pilot trains on about 64k transitions an iteration from C49-sd. A
  pilot-only bench arm (pace against a passive opponent) would then be the cheaper mechanism test.
- **12:47:** C131b reads R-null (#599), so the clock-payout line closes. C131's z 1.8 didn't replicate (new pair Δλ_T4 +0.028,
  Δλ_bE +0.009). Both payout levers (C130, C131) leave pace unchanged. Next: **C132** (A137; the goldfish under S-V and
  S-P search, #598), being built. Its band picks the next deep round's topic: training or credit, the value's targets, or
  representation, interface and horizon.
- **13:31, state for the next session:** C132 R-reach, C132b R-not-horizon, C133 R-candidates (#601-#607). The policy gives
  PlusPower and Item Finder about zero probability where a fast line plays them. **Pace correction (#607):** the
  uncontested gap is about 3 own turns (14 against 11 on wins of any ending), not 10+. The script decks out in 29%, and
  arm 0 never loses to the goldfish. Implementation was asked to fix the README's pace sentence. **Open for Evan (#607):**
  (1, default) a deep round on why oracle-timed PlusPower is worth only about an Energy here against human valuations
  (field HP thresholds, mirror, clock: rule 9); (2) sequence-level search with a probability floor; (3) bench pilot
  learning for near-zero-probability plays. Nothing is queued, and the GPU is idle. The deep round is held for usage
  (week 63% against 62.1% at 13:22).
- **16:19: deep round 5 done** (#608; #607's default; launched 16:13 at the week's line). Report: `reports/Tempo card value in
  2000 meta.md`. PlusPower is +10 after Weakness (engine code checked), so it flips knockouts only at exactly 10 HP left
  and pays through Gust's choice of target. **C134** (the breakpoint rates of the loop's field against the California
  lists') is recorded and handed off. The ground truth is California; New Jersey was Prop 15 (at most 15 Trainers, 26
  Energy). The next deep round is no earlier than 19:13.
- **16:50:** C134 R-same (the field isn't the cause). **C135 R-value-knows (#613):** the pilot's own value-scored full-width
  search plays PlusPower at 83% of 10-HP breakpoints against 0.4% greedy, and Prizes per own turn go .083 → .129. Queued
  (#614): **C136** (A138: PlusPower's price under search, timing against card flow, evaluation only) and **C137** (the loop's
  pilot learns from its own full-width search; seeds 28 and 29; staged; #106's signature as a stop rule). Training targets
  are SV only, never SP. No deep rounds while the week is over its line (65% against about 63.2% at 16:43).
- **17:00:** C136 reads between (#616-#617). PlusPower is 0.44 greedy and 0.50 under symmetric full-width search (S-PP's 0.59 is
  a one-sided edge). So learning its timing reaches parity with an Energy, not above. C137's bands stand with updated priors
  (Amendment 2); the build is under way. The still-unexplained part of the ground-truth gap: a tempo-card value above an
  Energy, which no player here has produced. If C137 is R-learned with no T4 rise, rule 9 sends the next check to the
  evaluation setting.
- **17:28:** the research-call watcher was reaped by Claude Code for low memory (3.8 GB free of 31.4 at 17:28). It was not
  restarted, per Claude Code's note. Calls and results reach this session by message from the other agents. C137 s28 is
  running and s29 is queued. Row 73's 2 GB RAM hold applies at boundaries.
- **17:58: C137 closed** (#621-#623). The fourth form of expert iteration fails at D 0.02 and 0.10 on #106's signature, with
  PlusPower 1.3-2.4% of kept targets. Nothing is queued; the GPU is idle. **Open for Evan (#623):** (1, default) a rule-9 deep
  round on why 2000 players valued PlusPower above an Energy when no player here does (opponents' play, matchup field),
  when usage allows; (2) card-neutral Prize-within-turn targets (rows 60 and 86 ruling); (3) sequence-level search with a
  probability floor; (4) pause and report. The watcher is not running (reaped for low memory).
- **18:42: Evan's row 112** ("restart, there was a result about finishing games quicker that made progress I believe") is read
  as C135. **C138** puts the pilot's own V-scored search (top 3 plus all legal Trainer plays, at Trainer-playable decisions)
  into the drafting loop's games (#624; Amendment 1). In S (s30) every game is searched and PPO masks searched decisions.
  In V (s32) every population game is searched and unrecorded, and PPO trains on practice games plus 500 unsearched games.
  A timed pilot sets 30 or 15 iterations. Handed to implementation, which builds now.
- **20:18: C138 closed** (#628-#630). Symmetric search in the loop doesn't speed games, since C135's gain was one seat against
  a greedy one. That answers row 112 on pace. **C139** (PlusPower's paired price against the California field, greedy
  against symmetric search, evaluation only) is recorded and handed off. R-search-favors would send a ledger-read C138
  rerun to Evan; R-parity means the gap is unexplained by anything tested.
- **20:29:** C139 reads R-parity with R-greedy-under (#632-#633). Greedy PlusPower is −0.054 against the field and searched is
  −0.003. Nothing tested makes PlusPower worth more than an Energy. **C140** (the same field price at a 60-turn clock and
  untimed, a rule-9 check) is queued as the default. Evan's options are in #633.
- **20:54:** C140 reads R-no-clock (#636: PlusPower's field price is −0.028 at 60 turns and −0.044 untimed, against −0.003 at
  20-45). C141 (Prize-scored search, A139) has been running since 20:54. It's the last split: the scorer against the game.
- **21:01:** C141 reads R-game (#637). Every player built here prices PlusPower at about an Energy: oracle timing, V- and
  Prize-scored search, any clock. **Open for Evan (#638):** (1) a deep round on human-level play beyond one-turn lookahead,
  and on whether paired-copy pricing can show a card's worth; (2) accept parity and aim the per-card goal at other cards;
  (3) pause and write up. Nothing is queued, the GPU is idle, and the watcher is off.
- **01:48:** C142 reads between (#641-#643). Every tempo card is slightly under an Energy under search, alone or as a package. Every
  cheap setting check is done. **For Evan (#643):** (1) a much stronger reference player (sequence search or ISMCTS,
  evaluation only); (2) a deep round on human valuations and paired-copy pricing; (3) pause and write up. Nothing is queued,
  the GPU is idle, and the watcher is off.
- **09:00: deep round 6 done** (Evan's row 113, #645-#646). Report: `reports/Card value under player skill.md` (thin: no per-card
  skill data). **C143** (a no-oracle strength ladder of PlusPower's field price, start → arm 0 → search → deeper search,
  with a head-to-head check) is handed off. The next deep round is no earlier than about 12:00.
- **09:18:** C143 is void (#648-#649). Research's gate error: use win share for head-to-head gates. General strength doesn't
  move PlusPower's price (start and arm 0 are equal), and only search timing does, to parity. Open for Evan (#649): a
  stronger reference player (weak prior), other Trainer groups under search as a positive anchor, or a write-up.
- **11:28:** Evan's row 114 ("3 then 2") is done. Write-up: `reports/2026-10-31 Night write-up.md` (#650). **C144** (the draw,
  search and disrupt groups under search against the California field; three 30-minute stages) is handed off (#651). If
  every group reads parity or below, recommend an engine-against-2000-game-records check to Evan.
- **11:56: C144 gave the first positive anchor** (#653-#654). Draw (Oak, Bill, Gambler) beats Energy in the California lists:
  +0.095 greedy, +0.114 under search. The drafts carry about 1 against the lists' 6. **C145** (a 2×2 of the loop's pilot
  against arm 0, and drafted decks against human lists; does adding 2 Oak + 2 Bill for 4 Energy help in the loop's own
  setting?) is handed off.
- **12:05:** C145 reads R-both (#655-#656). The loop's pilot undervalues draw (−0.058, 3.9 SE against arm 0), and draw added to
  drafted decks is worth +0.014 to +0.028. The coherence proxies don't explain the context effect (#657). Nothing is queued;
  the lead for Evan is the loop pilot's draw deficit.
- **12:48:** C146 reads R-provenance as a lead (#659-#660). Arm 0's strong draw skill came from the human bench lists; the
  human-free pilots value draw only weakly (+0.028 to +0.073). For Evan (#660): (1) practice on the population's best decks,
  (2) stronger selection for small gains, (3) pause. Nothing is queued.
- **13:44: Evan's row 115** (standing): take defaults, no open lists for Evan, log "taken by default". Only commits, pushes and
  rule changes wait. **C147** (head to head against arm 0, and play against hold at the loop pilot's Oak and Bill) and **C148**
  (half of practice from the population's top quarter, seeds 34 and 35) are queued (#661-#662).
- **13:59: Evan's row 116 done** (#665-#667). Deep round 7 report: `reports/State representation and exploration.md`. The queue was
  cleared (C147 stopped at (a): the loop's pilot loses 0.391 to arm 0; C148 dropped) and refilled: **C151** (re-test 1 SE winners),
  **C149** (mirror update: bandit, then bench), **C150** (pooled per-card Thompson proposals), **C152** (remaining-deck counts and
  thermometer inputs, bench). Lesson: write long records with the Write tool, not one big Bash heredoc chain.
- **15:04:** C151 reads R-noise (#679-#680). 1 SE winners re-test positive 49%, so per-move selection is noise. C149 closed (#672: one-step
  afterstates are biased toward attacks). C150 (pooled Thompson, per-deck samples) has been running since 15:03; C152 (count_features against
  control, bench) is queued after it.
- **16:24:** C150 reads R-harm (#682-#683; the Pokémon slide). C152 reads R-null on win share with a draw-price lead (+0.047; #684-#685).
  Queued: **C152b** (count_features at training seed 2), then **C153** (the posterior as a bonus on the head's logits, keeping Nf). The exploiter
  pilot isn't queued.
- **16:45:** A144's power check (#687). Outcome selection is 240-1,800× under-powered per move, and pooling 2-14× short. C153 was cancelled before
  launch. **C154** (is the pilot's own V at turn 3 a lower-noise paired signal than the outcome?) is queued after C152b. Usage flag from the
  auditor: week 75% against about 71.1% at 16:43, so no subagents and fewer records.
- **17:27:** C152b reads R-not (#690), so count_features closes (seed 2's draw price cf − c +0.005, SE 0.014, against seed 1's +0.047). C154 (the value
  signal, with bias arm L) has been running since 17:26 and takes minutes.
- **17:32:** C154 reads R-no-gain (#691-#692). The drafting chain closes on power (C151 coin-flip re-tests; #687's power numbers; C154).
  **C148** is reinstated, with the pilot's head-to-head strength on the California mirrors as its primary (0.391 now; R-stronger at 0.43 or more
  at both seeds 34 and 35).
- **18:09:** C154 is confirmed R-no-gain by its solo re-run (#695-#696). C148 is running (s34, s35). An implementation lesson (#693): Git's sh.exe
  launches a child bash.exe, so kill the tree, not the launcher.
- **18:46:** C148 reads R-not on pilot strength (0.346, 0.404 against 0.391) but has the best reported-only drafting pair so far (G1 4.33 and
  6.67, T4 3.17 and 2.50; #697-#698). **C148b** replicates it at seeds 42 and 43 with G1 and T4 as the primary. Prior R-null (selection over
  many screens).
- **19:48:** C148b doesn't replicate (#700-#701; practice from the population closes). **C155** (8 powered decisions an iteration at about 125 paired
  slots each, half held out; does selection become informative?) is queued, seeds 44 and 45.
- **20:51: C155 reads R-power** (#705-#706). With about 125 slots a decision, selection is informative (78% of kept moves hold on held-out games),
  and kept moves move shape toward the lists (+2.3 Pokémon, −2 Energy), not tempo or draw. Turnover drowned it. Queued: **C156** (concentrated
  practice, running, readout about 23:15), then **C157** (powered selection, 24 decks, turnover 0.04, 60 iterations, seeds 46 and 47).
- **22:49:** C156 reads R-not provisionally (#709-#710); K1m runs after C157. C157 has been running since 22:48 (powered selection, 24 decks, 60 iterations,
  seeds 46 and 47; power check at stage 2).
- **00:32: C157 reads Harm** (#711-#713). Informative selection, but too few moves (one every 4 iterations) to reshape the population; G3 dropped. Closed.
  K1m runs to about 01:15. No other lever with a case is written; the deep round is held for usage.
- **01:08: C156 closes R-not** (K1m, #715-#716). The queue is empty and the GPU idle. No lever with a written case is left. The deep round is held for usage
  (week about 79% against about 73.8% at 00:43). The next round's topic, when allowed: how a human-free pilot can acquire the transferable draw
  skill arm 0 shows on held-out lists (curriculum or self-play methods that produce coherent strategies; deck-builder co-evolution with pilot skill).
- **04:44:** A147 becomes **C158** (#717): 4 fixed concentrated rules-only decks, start recipe for 30 minutes, two training seeds, priced on the 20 held-out
  lists' draw group. It tests repetition against content for arm 0's draw skill, with an uninformative clause under 8 draw copies.
- **04:46:** C158 closed before launch (#719), uninformative by design: 4 generated decks average about 2 draw cards, and resampling would select on
  names. A147's question stays open. The queue is empty and the GPU idle. The next deep round (topic: how a human-free pilot gets the transferable
  draw skill) is held for usage (week about 80% against about 75%).
- **04:46:** C158 is reopened (#720) with a matched design: F (4 concentrated decks with 2 or more draw copies) against M (128 such decks), two training
  seeds each, on the 20 held-out lists' draw price. It tests repetition with draw density held fixed. Selecting decks is allowed because it's a
  diagnostic (the auditor).
- **06:54: C158's key result** (#722-#723): practice on concentrated decks with draw cards (M) gives arm 0's held-out draw skill (+0.083 against +0.089;
  head to head 0.43 against arm 0). So draw skill is exposure. Waiting on Evan: may the loop pilot's practice decks use card-neutral, concentrated
  coverage of the whole pool? It's a no-prior-rule question, so nothing is launched.
- **07:00:** C159 is withdrawn (#725-#726; a card-neutral rotation can't raise per-card exposure). **C160** (practice weighted by the pilot's own under-play,
  4 Trainers at 3 copies, practice at 750 games) is written and runs only on Evan's yes. The question for Evan is in #726.
- **07:10:** C160 is closed before launch (#727-#728): play-when-legal picks situational cards, not draw. **C161** (evaluation only: per-Trainer search-against-greedy
  disagreement on the loop's games) is queued. If it reads R-signal, the training question goes to Evan (#726).
- **07:28:** C161 reads between (#730-#731): search disagreement flags immediate effects, not draw. No card-neutral exposure signal found. Waiting on Evan's ruling (#723/#726);
  the GPU is idle. If a deep round is allowed, its topic: card-neutral curricula that credit delayed-payoff actions (longer-horizon credit for exposure targeting).
- **08:45:** #723's claim is corrected (#732): draw-rich practice is a lead, not shown (M − K1m about 1.7 SE). **C162** (draw cards under arm 0 in rules-only decks of
  the lists' shape, against drafted decks) is queued. If it reads R-shape, powered selection on shape is the card-neutral lever.
- **08:51: C162 reads R-not-shape** (#734-#735). Draw pays only in coherent decks, even for arm 0. The loop must find coherence before draw cards can pay. Nothing is queued and
  the GPU is idle. The next round's topic: how a drafter discovers coherence without human lists. Held for usage.
- **11-01 18:03 (session 1616bbee):** deep round 8 launched, taken by default (row 115, #735's topic): `research_notes/Drafter discovery of deck coherence/`, one Haiku researcher plus a Sonnet writer. Crossover and linkage appear nowhere in the log, hypotheses or earlier notes, and H97 (valley test) is still untested. Usage at 18:00: week 84% (line: 84% now to 92% at 11-03 08:00, 0.21 a hour), 5h not in file. Watcher: scratchpad watch_audits.sh, baseline 31 calls, 90-minute fallback. The names don't resolve; four cc-msg pipes exist (4f1e87, 3f3f70, 7b8429, 1acde4), one of them this session. No audit since A148 08:43, and the GPU has been idle since 08:50.
- **11-01 18:05:** round 8 stopped about 2 minutes in, with no report and its empty folder removed, because A149's call (18:03) puts the crossed test first. **C163** (`runs/probe/C163-draw-deck-field/record.md`, #737) is handed to implementation through the cc-msg pipes. Its bands pick the next step: R-deck or R-both reopens the coherence round, opening on crossover and linkage (absent from all notes) and H97's untested valley test. The stopped round isn't counted against the 3-hour limit. Watcher re-armed, baseline 32 calls.
- **11-01 18:25:** C163 reads R-no-gap (#741), so the coherence round doesn't run and #735's reading is withdrawn (#742). Proposals set draw's count (60 × 3.1% = 1.88 against 2.44, 1.90; lists 5.92), and selection can't resolve +0.007 a copy. **C165** (`runs/probe/C165-trainer-factorial/record.md`) is handed to implementation at pipe 3f3f70; auditing is pipe 7b8429; this session is 1acde4. R-signal leads to C166 (the table as a proposal bonus); R-no-signal reopens the deep round on search for co-adapted sets. Next free record number after C166: C167.
- **11-01 18:34:** the auditor's review corrected #742 (#744). C165 Amendment 1 written; **C167** (body × Trainers cross, the 18:28 call) written. New fact: fresh 30-iteration screens read mostly the generator (time constant about 93 iterations, wide immigration; long line at 499 has draw 7.61, T4 1.20, one lineage). Next record: a long fresh run on engine K testing wide turnover. Watcher needs baseline 33.
- **11-01 18:37 (#745):** **C168** written (long fresh run, wide immigration on and off, 130 iterations, TV as the per-card metric). Queue order: C167, C165, C168. Next free record number: C169 (C166 stays reserved for C165's follow-up).
- **11-01 18:39 (#747):** survivors' paired change is the undiluted direction read (43 screens: T4 −0.26, draw +0.12, T −1.64 per 25 iterations; selection, not proposals, drives T4's fall). C168 amended; T4-only stop declined, with reason, and C168 doesn't address T4. Open: why every player here prices T4 at or under an Energy.
- **11-01 18:41 (#748):** C168 Amendment 2: band on E (TV minus permuted null); stop at 60 if N − W > −0.01 at both seeds. Auditor accepts the run. T4-ladder question goes to A150; check prior attempts (C139-C143, C161, #646-#649) before recording anything on it.
- **11-01 18:54 (#751):** C167 Body +0.28, Trainers +0.04-0.06 (between; replication post hoc). Drafted bodies far from the lists', and G1 can't see it. C169 splits Body. Deep round 8 running (`Drafter search for coadapted decks`). Next free record number: C170 (C166 still reserved).
- **11-01 18:57 (#752):** C169 Amendment 1: the lists join as a field, read on logit. Round 8's report is written, unread and held; turn it into records only after C169 reads, and only if Identity doesn't carry. Round 8 hasn't delivered, so the 3-hour clock counts from its launch at 18:54 for the next round.
- **11-01 18:59 (#753):** long line = walls (Snorlax, Chansey) with draw about 10 and T4 near 0; not rediscovery. C168 Amendment 3: R-walls stop, prior for N is R-walls. Check why a flag exists before varying it.
- **11-01 19:20 (#758):** C165 between; C166 closed on its gates. Oak, Energy Removal, Bill above Energy under all 4 pilots, others below. Additive fit predicts the gap (arm 0: +0.294 of +0.336, Pokémon +0.222). Waiting: C169, implementation's two CPU reads.
- **11-01 19:42 (#763):** C169 R-identity (replicating). Round 8 closed unused. **C170** written: table bodies against the lists. R-table-works leads to **C171** (table on the head's bonus path, centred within supertype; control is C168's W). Otherwise C168 launches as written. Next free record: C172.
- **11-01 19:44 (#764):** C170 Amendment 1. C171's κ only from the drafted field; lists only gate. Gate also needs decided wins and uniform-Trainer cells.
- **11-01 20:07 (#768):** C170 R-table-works, C171 written (table at κ 3 on init, turnover and proposals; W control at seeds 48, 49; A after B's read at 30). Printed-card check first. C168 N unlaunched. Rule 3 flag logged for Evan. Next free record: C172.
- **11-01 20:10 (#769):** C171 Amendment 1: R-start and R-learns, new-table gate, plain-table test, R-narrow band. C172 written (four colourless Basics, greedy and search). Next free record: C173.
- **11-01 20:14:** Claude Code stopped the research-call watcher for low memory. Not restarted, per its note. Calls now reach this session only by message; the auditor is told. Baseline was 33 calls.
- **11-01 22:00 (#790):** C172 R-easy-to-pilot; B holds. **C173** written: stage A (Y against E2 under search), R-holds reopens B; else stage B (table fitted under search, top 60 names). Next free record: C174, reserved for B on a search table.
- **11-01 23:29 (#801):** W s48: passes the lists' shape near 23, slides to 13/23/23 by 54 (one seed). C173 B1 is next (42 Trainers' β under search against greedy, C49-sd, concentrated decks); B2 after. B held. Next free record: C174.
- **11-02 00:44 (#812):** C175 written (Trainer factorial on strong bodies, A151). W s49 resumes after it if free RAM allows. Next free record: C176.
- **11-02 03:08 (#833):** C176 written (sampled-play factorial; the loop's games aren't greedy). Greedy Energy Burn loop under test by implementation. Next free record: C177.
- **11-02 04:46 (#846):** C178 R-not, underpowered. Loop climbs the table's value unaided (top 12 v 0.6 to 1.3, lists 1.61). W s49 stopped on research's call. Waiting: seed 49 12 pods, C177, C176. Open: strength rises on a human-free signal, in the wrong shape; every price read here is under pilots that price Trainers below Energy. Next free record: C179.
- **11-02 05:13 (#851):** C179 between, pilot-dependent (+0.073 C49-sd, +0.017 arm 0). C180 written (same dose under K1m, C127 s16, W s49's net, M1, arm 0 s2). W s49 stopped at 83. Next free record: C181.
- **11-02 05:18 (#854):** B1 flat at both seeds (claim on this rung, rules-only bodies); relative rise repeats as a lead. B2 held. Waiting: C177, C180 stage 0, C176.
- **11-02 05:28 (#856):** C177 R-falls (G3's rise is greedy flattery, one seed). C180 stage 0 holds, R-set. If stage 1 shows set value under human-free pilots, read round 8's report for Trainer packages, not bodies.
- **11-02 05:51 (#864):** M replicates. **C181** written: practice weighted by the plain Trainer table, controls W1 and W2 first. Next free record: C182.
- **11-02 05:56 (#869):** **C182** written: Trainer table on the drafter (init, turnover, proposals), W as control at seeds 48, 49, primary survivors' Trainers and median T at 44. C181's training waits. Next free record: C183.
- **11-02 06:15 (#875):** Gap to lists doubles under search. R-set weakens; draw may carry the other Trainers. **C183** (interaction in existing factorials). Next free record: C184.
- **11-02 08:05 (#883):** D s48 at 29: G3 0.507 under C49-sd, G1 7.4, one seed, greedy, mostly start decks. Search read is decisive. Band at 44.
- **11-02 08:07 (#884):** **C184** written (recovery from T 13-17, table against uniform, seeds 50, 51). C182 described as 'held under greedy'; §3 unmet. Next free record: C185.
- **11-02 09:02 (#889):** C182 between at 44, C185 between (−0.065, −0.017 under arm 0). G1 5.07, 7.43. Waiting: search on D; decide D extension or C184.

## State at 2026-11-02 10:58 (research session 1616bbee; GPU paused by Evan at 10:56:59)
- **Don't touch runs/GPU-PAUSE.** DR s50 and s51 stop at their next iteration (about 20-23) and resume with --resume. Held: DR, WR, D's search at 44, M2, C180-w, C176's s49 and w. Calls reach this session by message; the watcher was reaped for memory and not restarted. Pipes: implementation 3f3f70, auditing 7b8429, this session 1acde4.
- **Chain (log #737-#895):** C163 no gap on draw's price. C165 factorial: most Trainers below Energy under all pilots; Oak, Energy Removal and Bill above it. C167 and C169: the lists' strength against weak fields is which Pokémon. C170: table bodies beat uniform against the lists; C172 easy to pilot, so the Pokémon-table arm B holds. W s48, s49: Trainers fall, slide toward Energy, G3 rises only under greedy (C177: −0.137 under search). C173 B1: search doesn't lift Trainers' value, flat at both seeds; the lists' cards rise relative to the rest by about +0.002 (a lead). C175: strong bodies don't help under greedy. C179 and C180: shedding gain is mostly lists decking out under pilots that overdraw; M replicates at two seeds. C182 D (Trainer table on the drafter): Trainers hold where W's fall, G1 5.07, 7.43 at 44, G3 0.53, 0.49 under C49-sd, −0.065, −0.017 behind the lists under arm 0, 0.351, 0.366 under search against 0.505. Band between. Archetypes 1, 0 of 8; T4 1.57, 1.33. §3 unmet.
- **Next on resume:** C184 DR's read at 29, then WR at matched iterations; D's search at 44; C181's control. Decide D's extension past 44 after C184. Rule 3 flag and the concentration ruling are with Evan (plain tables keep the ruling moot). Next free record: C186.
- **Usage:** week 84% at 10:56, 5h not in file; no subagents since round 8's researcher and writer at 18:54-18:57.
- **2026-11-02 12:45 (#899):** bonus raises Trainers' mass (my error); DN arm replaces DR on resume; C186 written (search-fitted table). Next free record: C187.
- **2026-11-02 12:48 (#902):** C187 (W with head frozen; H94 never ran), neutral D, DN all queue after the pause. Next free record: C188.
