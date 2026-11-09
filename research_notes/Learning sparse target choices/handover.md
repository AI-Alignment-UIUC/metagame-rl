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

## State at 2026-11-04 13:28 (research session 1bd81eeb; GPU paused by Evan since 11-02 10:56:59)
- **Don't touch runs/GPU-PAUSE.** Pipes: implementation 6fd965 (name "implementation"), auditing 512f86 (inferred, not confirmed), this session c1e624; 390ac1 is the neuro project's session and 932857 is 333-0f. Watcher: scratchpad watch_audits.sh, matches new RESEARCH CALL lines except "no new question", 90-minute fallback.
- **Deep round 9 done** (13:13, week 6%, 5h not in file; Haiku researcher, Sonnet writer): `reports/Shared policy across many decks.md`. Next round no earlier than 16:13. Its run: **C189** (specialist dividend against Trainers; after W0).
- **Chain (#910-#915):** W's cut sits in the head's weights (#912), and it's mostly a cut of small stacks (C188 stage 0: γ −0.67, −0.98, between by the letter). The head's bonus is entropy over ids, whose optimum is s = −log(copies); β 0.03 steepens γ 2.33 times (R-β-steepens; T's ratio between). A164 found the same independently. Not settled: its iid-noise replay drowns the bonus, noise uncalibrated.
- **Queue on resume:** W0 (bonus off) s48, s49 first; WK (−KL from copies) with H0 s48; DN, ND, C186 after W0's first read; C189 after W0. Implementation builds `--draft-out-bonus` and ports A164's replay with calibrated noise. Next free record: C190.
- **Lesson:** two citations of mine were wrong when first written (#915), one from a number I recalled and not checked. Check log numbers before citing them. On Git Bash, PYTHONPATH needs Windows form with semicolons for the venv's python.
- **11-04 13:46:** C188 Amendments 2-4 (#916-#917). Auditor reviewed; W0's stop and C189's groups changed. A165: k passes −1, so the bonus can't finish it. Free read of real slots: R-size, −0.012 a copy moved at both C150 seeds and C153. **W0S** (bonus off, size-neutral credit) is queued beside W0; WS and WK only if it moves something. Uncapped Energy-to-Energy not tested alone. Implementation's builds: `edit_slots.jsonl` (required), `--draft-out-bonus`, `--draft-size-neutral`, stage 1's port. Auditing is confirmed at pipe 512f86. Next free record: C190. Next deep round no earlier than 16:13, and it needs a real question first, not the clock.
- **11-04 14:01:** C188 stage 1 reads R-unexplained at the calibrated rung (#920): β alone T 1.06, 1.08 against W's 1.37, 1.44; no plant at measured size reaches 1.20. Unbanded, post hoc: at tau 0, Pg −0.012 with the bonus matches W's norm and passes −1. Not chosen as the explanation. W0S's λ and `edit_slots.jsonl` decide. Research reads on this line are stopped until W0 runs (A166, #919). W0, W0S queued and holding on GPU-PAUSE. Waiting on Evan's resume; nothing else queued from research.
- **11-04 15:34:** 90-minute fallback, no new call. No deep round at the 16:13 slot, taken by default (row 111: on a call or when no written lever is left; about 9 written arms hold on GPU-PAUSE, and research reads on this line are stopped until W0). Week 7%, 5h not in file. The watcher is re-armed; it skips lines reading "no new question" or "no new CPU work".

## State at 2026-11-06 15:16 (research session a99a25a7; Evan's row 120 resume at 15:10, GPU-PAUSE removed 15:12)
- **Watcher:** this session's scratchpad `watch_audits.sh`; wakes on a new `^RESEARCH CALL` line that doesn't read "no new question" or "no new CPU work" (baseline 49 of 61), 90-minute fallback (about 16:45).
- **Queue:** C188's queue started 15:13:53; W0 s48's launch was refused at 15:13:54 by the 80% GPU gate (12.7 of 15.9 GB in use, neuro's). Implementation is tailing the C188, C187 and C184 logs. Names don't resolve; five cc-msg pipes (5f5c66, 228ba3, 21fe4d, 59f713, 511599), owners not mapped.
- **No deep round at this slot, taken by default (row 115):** no open call (A169's is "no new question"), about 9 written arms wait with W0 as the discriminator, and the GPU is at its cap. Already covered, so not candidates: noisy selection and racing (round 7), entropy against a base measure (the methodology report). Usage at 15:12: week 25% (47% of the week elapsed; reset 11-10 08:00), 5h not in file. No agents spawned.
- **16:50:** A171's 16:45 call became **C190** (`runs/probe/C190-edit-channel-split/record.md`, #929), a CPU split of W0S and W0's shape at 44 into the start, in, out and group terms, with a start term added to A171's band. It's handed to implementation, which confirmed and is building it, with the read at about 17:27. **Pipes:** implementation 21fe4d (from its own reply); auditing is 5f5c66 or 59f713; 228ba3 is stale; this session is 511599. README: block #921–928 closed (Recent had been mislabeled 922–928), Recent is #929. Next free record: C191.
- **17:31:** C190 seed 48 (#931-#932): R-held on both arms by the letter (S 5.89 and 5.38 against K −1.99 and −1.07). Trainers read R-cut-same (kept cuts −9.50 and −9.47); W0S holds its Trainers through in-adds. Selection keeps fewer Energy cuts than are proposed (reported only). **C191** (`runs/probe/C191-energy-start-bracket/record.md`): WL = W's recipe plus `--init-e-range 10-14` and edit slots, seeds 52 and 53, beside C184's WR (the high side), with W s48 and s49 as the middle. Bands on the late window's edit drift: R-attract (sub-bands lists, high, low), R-flat, between. Handed to implementation (21fe4d). #933 corrects my estimated "17:40" to 17:31. README Recent is now #929–933. Next free record: C192.
- **17:44 (#934-#935):** WL is built and queued (`queue_c191.py` pid 15900). The sampler accepts 10.6% and 12.5%, and WL starts at P/T/E 9/38-39/12-13. At population level, edits cut 2.6-7.2 Energy over iterations 1-44 and turnover refills 2.8-5.6, so R-held's "never taken out" wording was wrong (#935). C191 Amendment 1 adds R-down and makes R-flat two-sided. **C192** (`runs/probe/C192-turnover-energy-split/record.md`): turnover's Energy split into kill and dilution, CPU, handed to implementation. My script: scratchpad `turnover_term.py`. Next free record: C193.
- **17:47 (#936-#937):** C192 seed 48. The Energy kill share is 0.48-0.60 (W0 R-kill; W0S and W between). In every arm, selection works against Trainers: turnover's kill −1.8 to −2.6, mutants −0.4 to −1.4. W0S's edits move T only −0.71. So under size-neutral credit the Trainer fall is mostly selection's, back to the games' pricing. W's games deck out only 1.4% (#878), so deck-outs aren't the cause. No new record: the per-card pricing (C165) already covers it. C191 Amendment 2 adds C192's split on WL. Waiting on the s49 arms at 44, then WL. Next free record: C193.
- **19:26 (#938-#940):** W0 s49 stopped at 40 on C168's relative slide rule, which puts the line at P 15, inside §3's band. **C188 Amendment 7** makes the line absolute, median P above 18.5 at 3 reads, for all C188 arms still running or queued. W0 s49 resumes 40 → 44 when a slot frees. W0's "bonus necessary" branch is already out at both seeds. C192 on W0 s49 at 39: corr(score, T) −0.48 among removed decks. Waiting: W0S s49 at 44 (about 19:52).
- **19:56 (#942-#943):** W0S at both seeds: C190 R-held, met. C192 between (0.48, 0.507). C188 no band. Ground truth R-no. W0 s48's ground truth is Harm (G1 mean5 23.43). #943 corrects #937: W0S's edit T drift is −0.71 at s48 and −2.80 at s49, so "mostly selection's" was one seed. WK is unconditional by the record. WU (on R-game, not built) waits for H0's read. Waiting: W0 s49's resume to 44.
- **20:08 (#944-#945):** C188 closes. W0 is R-game at both seeds, so the cut is learned from the game signal. No head-side change moves the ground truth. Every level of game-based selection prices Trainers below Energy, so the gap is the pilot and the field (C139-C165, C162's coherence gate). WU (R-game's next arm, not built) waits on H0 at 44; WK is running (s48 since 20:05). No deep round: co-design (round 1, `--protect`), noisy selection (round 7) and crossover (round 8, unused) are covered. README Recent is #945.
- **20:46 (#946):** auditing (pipe 59f713) sent A172's call (depth against field/coherence). **C193** (`runs/probe/C193-lists-swap-depth/record.md`): the lists against 4-copy swap variants (L−T, L+T) under C49-sd, greedy against C135's search, 2 game seeds, ahead of WL. The swap is 4 copies, not 1, for power. Prior: C96's flat lift (#321-#324). Handed to implementation and auditing. Watcher now matches C190, C191 and C193. Next free record: C194.
- **20:47 (#947):** C193 Amendment 1, with all three of the auditor's points: pooled bands at 0.48/0.52 (my 2-SE error), a search ≥ 0.55 strength gate, and per-name M_minus.
- **20:50:** Claude Code reaped the research-call watcher for low memory (3.9 of 31.4 GB free at 20:50), and per its note it isn't restarted unasked. Calls and results now reach research only by message from implementation (21fe4d) and auditing (59f713), and both are told. Row 73's 2 GB hold applies at run boundaries.
- **20:52 (#948-#949):** C193 built (`c193_run.py`, `queue_c193.py` pid 49328) and checked against the record. Amendment 2: hard order before WL; the Trainer-plays report dropped. Its pilot waits on RAM (4.7 GB against 6.5) and GPU memory (10.8 of 12.7 GB).
- **20:57:** C193 stage 1 launched (driver pid 40196: gate, greedy, search-minus, search-plus; 75-minute kills). The pilot: 45% decisive, so pooled SE about 0.010; a power note is in the record, and the thresholds are unchanged. WL can now launch beside it. Waiting on implementation's message with the gate result.
- **21:30 (#952-#953):** H0 s48: proposals Trainer-neutral, but Trainers fall through selection, and G1 mean5 16.7 against W's 14.2. **WU dropped** (C188 Amendment 8). Correction: C193's stage 1 hadn't played at 20:57; its gate is refused on RAM (4.7 GB) and GPU memory (10.8 GB).
- **21:55:** C193's gate passes on s1 (search against greedy 0.7145, SE 0.0088); 85% of games are decisive, so pooled SE about 0.007. s1-greedy is launching, then search minus and plus. WL was released at 21:40:40.
- **22:01 (#955-#957):** C193 greedy s1: M_minus 0.4545, M_plus 0.5927 (Energy preferred at both margins). Amendment 3: fixed-list SE, seed 2 runs, per-name effects read within list (list 16 at 0.24 confounds Defender and Trader). #957 corrects my #661-era citation to #663.
- **22:02:** C193 fixed-list SE, greedy s1: M_minus 0.4545 (0.0085), M_plus 0.5927 (0.0073). List 16 = Viray's Rain Dance; Defender and Trader read about 0 within list, so no rule-9 flag. Challenge! −0.114 and Pokémon Center −0.175 within list, one list each: watch under search. Seed 2 queued (driver pid 48740). s1-search-minus is retrying on RAM (6.0 GB against 6.5).
- **22:13 (#960):** C193 Amendment 4: no new screen launches while a C193 cell waits; running ones stay. WK s48 at 44: T ratio 1.208 (between), median 15/23/22.
- **22:15:** Amendment 4 applied: `runs/loop/HOLD-SCREENS` (hold_c193.py pid 48144, written 22:15:04) blocks new screen and pilot launches until C193-s2-search-plus registers; probes and --resume are exempt.
- **23:08:** C193 s1 search-minus: 0.4677 (fixed-list SE 0.0102) against greedy 0.4545, lift +0.013 (SE 0.019); both under 0.48 on s1 (R-pilot-value's side, pending pooled). 86% decisive under search against 42% greedy. No rule-9 flag. Lead: Computer Search sits below the list's other Trainers within list (−0.036 greedy, −0.050 search, 22 lists). s1-search-plus launched 23:08:11.
- **23:27:** WK s49 at 44: T ratio 1.245, median 14/23/22; R-no at both WK seeds, not Harm. C188 line closed: W0, W0S and WK change the cut's speed, but none moves the ground truth. C193 s1-search-plus resumed after a GPU-rule hold (23:11:59 onward).
- **23:38 (#965):** C193 s1 complete: both players prefer Energy at both margins (M_minus 0.4545/0.4677, M_plus 0.5927/0.5910). **C194** (`runs/probe/C194-lists-swap-horizon2/record.md`): horizon-2 search, conditional on C193 pooling to R-pilot-value or a near-flat between; handed to build. Next free record: C195.
- **23:42 (#967):** C193 s2 greedy on seed 1's side (pooled about 0.452, 0.588). C194 Amendment 1: a RAM reservation (8.0 + 6.5 GB) replaces the blanket screen hold.
- **23:43:** C194 Amendment 1 applied: HOLD-SCREENS carries reserve_gb=6.5, so a screen or pilot launches only at ≥ 14.5 GB free; probes and resumes are exempt.
- **00:04 (#970):** C193 closed, R-pilot-value by the letter (search 0.4743, within 1 SE of 0.48); search lift +0.023 (2.4 SE); M_plus above 0.58 both ways. C194's condition is met and its gate pilot is next.
- **00:06 (#971):** C194 GPU pilot cut 0.1% of lines at maxSteps 40. s1-gate (h2 against h1, 4,800 games) launched 00:05:51; cells only if ≥ 0.53 at SE ≤ 0.010.
- **00:35 (#972):** C194 gate 0.5308 (SE 0.0083), just over 0.53, so h2 is only slightly stronger than h1. A note in the record says R-still-low would be weak evidence. Cells s1-search-minus and plus are running (pid 12972).
- **00:46 (#973):** A173 became **C195** (`runs/probe/C195-trainer-policy-engine/record.md`): C116's branch test on C49-sd for the top-10 Trainers, plus engine B1 (build) and B2 (scripted, with the changed reducers). The play-rate band is replaced (#728). No Trainer file has changed since e04c27e. DN s50: no stop at 41. Next free record: C196.
- **00:47 (#974):** C195 Amendment 1 (the auditor's limit): R-value doesn't clear policy, since both branches use the same pilot; a search-continuation add-on for Oak, Bill and Computer Search, reported only.
- **00:47:** C195 Amendment 2: the add-on trigger needs +0.03 and 2 SE, pooled over Oak, Bill and Computer Search.
- **00:57 (#976):** C194 s1 M_minus at h2 0.5035 (+0.036 over h1, SE 0.016): parity at two turns, between at s1. C195 Part B clean. DN s50 between (+2); DN − WR unreadable (WR at 4).
- **01:25 (#978):** C194 s1 complete: h2 M_minus 0.5035, M_plus 0.5415, so both margins move toward Trainers. C195 A-s1: PlusPower Δ_skip +0.037 (R-policy at the edge); Oak, Computer Search and Scoop Up holds right; Bill and ERs under-sampled.
- **01:43 (#980):** C194 pooled M_minus at h2 0.5008, between (parity). Depth lifts the Trainers' price to parity, not above. Next record idea: a searched judge in selection (C138 never read shape); write after C194 M_plus s2 and C195 A-s2. Reservation released 01:42:18.
- **01:55 (#981-#982):** C195 closed between (holds right for Oak, Computer Search, Item Finder, Scoop Up; PlusPower +0.034 and Gust +0.038 under-played; engine clean); the add-on was dropped. **C196** (`runs/probe/C196-loop-decks-swap-depth/record.md`): the swap read on W's own top-24 decks, greedy against h2 (premise check for a searched judge). Next free record: C197.
- **01:56 (#983):** C196 Amendment 1 (the auditor): an L+T' direction from iteration-0 Trainer names (survivorship); "coherence first" needs D and D' flat; +0.049 is two steps, not a slope.
- **01:56:** C196 built and queued (driver pid 24596): set A W s48 top 24 (median 15/21/23.5), set B W s49 (17/20.5/23); L+T' uniform over the 42 iteration-0 Trainer names; 576 variants a set, 0 illegal. Runs after C194-s2-search-plus.
- **02:07 (#986):** C194 closed between. At h2, M_minus 0.5008 and M_plus 0.538, so the lists' Trainer count is about h2's optimum; greedy was well below. C196's pilot launched 02:06:32.
- **02:08:** README: closed block #977–984 (Recent had run to 10 entries), Recent is #985–986, and the C193/C194 depth read is added to Where things stand's last sentence (5 sentences).
- **02:50:** C196 set A: greedy M_minus 0.4441, h2 0.4600, D +0.0157 (SE 0.0104) against the lists' +0.049, between at A. pplus at h2 running, then set B. WL s52 launched 02:08.
- **03:39 (#989):** C196 Amendment 2: reservation on GPU memory and RAM for its remaining h2 stages. WL s52 at 14: Energy drift +0.354 (W −4.94 and −2.45).
- **03:40:** C196 Amendment 2 applied (reserve_gb 6.5, reserve_gpu_gb 3.0; HOLD-SCREENS by hold_c193.py pid 4256), holding until C196-setA-h2-pplus2 registers; it re-runs all 24 set-A decks last.
- **04:12 (#990-#991):** C196 kill-while-held fault fixed (setA-h2-pplus is killed on leaving its hold, and pplus2 redoes it). WL s52 at 29: edit Energy drift +3.505 (W −6.59, −2.83), median 10/35/14. The R-attract shape, early, one seed; a rough crossing at about 16-18, confounded by WL's 38-Trainer start. The band reads at 30-44.
- **04:25 (#993):** WL s52 at 44: G1 mean5 4.83 (board best), median 11/29/19, but a transit (E rising +0.44 an iteration; drift grows with time; Trainer cuts on the 38-T start). R-attract can't be read without WR. Amendment 3: WL s52 resumes 44 → 74 after C196, with rest and W-level stops.
- **04:26:** C196 set B greedy: M_minus 0.4301, M_plus 0.5138, M_pplus 0.5357; setB-h2-minus next. C191 Amendment 3 queued (queue_c191b.py pid 28028; WL s52 to 75 after C196-setA-h2-pplus2 registers; readouts.jsonl every 5).
- **04:44 (#996):** C196 primary R-depth-transfers by the letter (D +0.0313, SE 0.0075, 0.0013 over the line, by C195's wording convention); sets A +0.016, B +0.047. Next record (C197): a searched judge, but cost is the problem (h2 is about 15 min an iteration estimated, so a 30-minute stage is 2 iterations). Design idea: fork W s49 at its population_it0044 snapshot (net and drafter included), with selection scored by h2 games and PPO as W; control is W s49's own 45-83; mechanism readout is the selection ledger (accepted − proposed T a move), then median T and G1. Write it after C196's L+T' cells. Usage week 32% (t 04:43).
- **04:46 (#997):** Conceded A174's point: C196's primary reads between, direction replicated (not R-depth-transfers). **C197** (`runs/probe/C197-judge-rerank/record.md`): re-rank W s48/s49 at 44 by h2 z against greedy (plus a G2 noise floor); R-judge needs ΔT_H ≥ +2 and beyond the noise. It runs before any searched-judge drafting. Next free record: C198.
- **04:49 (#998):** C197 built and queued (driver pid 35400; reservation until C197-s49-G2). C191 Amendment 4: WL s52's resume waits for C197-s49-H.
- **04:58 (#1001):** ND s48 at 44: median 13/23/24, T = W's 23, survivors' T −2.7; G1 mean5 8.6 against W's 14.2, from the P/E side; no band (method read). Reservation now binds resumes; WR s50 paused after iteration 5 until C197-s49-G2.
- **05:01:** C196 set B L+T' at h2: D' = M_pplus(greedy) − M_pplus(h2) = 0.5357 − 0.548 = −0.012 (SE 0.010). Depth doesn't raise the price of pre-selection Trainers on set B, only that of the decks' own (L−T +0.047). One set; log the combined read after setA-h2-pplus2.
- **05:35 (#1004):** Implementation's post hoc split of C196: in loop decks the Trainer-price part is +0.012 and +0.007 against the lists' +0.050; set B's D is mostly both-worse (+0.037). C197's prior moves to R-drift. Method lesson: pre-register the price and both-worse split in swap reads.
- **05:52 (#1006):** C196 closed: D between (price part small), D' flat, so no depth gain for discarded Trainers. Coherence is the next lever if C197 reads R-drift: round 8's block operators (crossover with repair, line swaps, consolidation), never run.
- **06:18 (#1009):** C197 R-drift at both seeds; the deeper-judge line is closed (no searched-judge run). Energy-type coherence checked and not recorded (C169 Fit about 0). Next: C189 (pilot skill on Trainer-rich decks), WL extension, WR. The practice-deck rule question is restated for Evan in #1009.
- **06:20 (#1010):** Reworded per the auditor: selection under this pilot at any tested depth favours low-T loop decks (H0 #953), so the lever is pilot play (C189). **C198** (`runs/probe/C198-typed-cost-check/record.md`): a rule-9 typed-cost engine check plus colourless and typed cost shares, before C189. Next free record: C199.
- **06:20:** C189 Amendment 6: --busy-ok only skips ar/'s 4 GB bar (the 80% cap and row 73 still bind); budget fixed in transitions at C158's alone 30-minute count, wall time up to 75 minutes. C198 runs before C189.
- **06:28 (#1012):** C198 closed: A clean; B R-typed-dead by the letter, but the follow-up is answered by C132 (attach 93-100% when held) and C169 Fit (on-type fix under about 0.03). No C199. C189 launched (pid 26760), waiting on RAM (1.4 GB). Asked the auditor whether C169's setting transfers; if not, a direct on-type fix of W's top 24.
- **06:29 (#1013):** **C199** (`runs/probe/C199-offtype-replace/record.md`): W's top-24 off-type basics replaced by (a) on-type basics or (b) the deck's own Trainers, against the original, greedy and h2, ahead of C189's training. #1013 corrects #1012 (dismissed too quickly). Next free record: C200.
- **06:31:** C199 built and queued (driver pid 22024). k: set A 21 decks (1-20 off-type each), set B 17 (3-20). C189 restarted (pid 4484) to wait for C199-setB-h2. C199's pilot is waiting on RAM (2.0 GB at 06:30).
- **06:40 (#1015-#1016):** WL s53 stopped at 5 by RAM-critical (06:37); queue_c191c (pid 43456) resumes it after C189's hold. C197's C49-sd column requeued after C199-setB-h2. Running: DN s51, C197-s48-G1-C49. RAM is the limit (1.4-2.0 GB free).
- **06:50 (#1017-#1018):** C199 greedy: S_a 0.547 (R-fit-transfers; #1012 was wrong), S_b 0.426 (R-trainer-harm by the letter; caveat starvation versus misplay, rule-9 replay with starvation markers). **C200** (`runs/probe/C200-ontype-moves/record.md`): why the +0.047 on-type fix isn't taken (not proposed, not kept, or refilled by wide_deck's 25% rule). Next free record: C201.
- **06:51 (#1019):** C199 Amendment 1 (arm (c), k−2 on-type + 2 T) and C200 Amendment 1 (R-cancel; no hand fix to wide_deck). Consistency estimate: S_b's −0.074 matches the generic Trainer price, so it needs no misplay.
- **06:56 (#1022):** C200 R-not-proposed (0.39% of picks; refill by wide entrants 52-71%; R-cancel uninformative). C199 (c) decides whether on-typing frees Trainer slots; if R-saturated, record a learned route to on-type.
- **06:58:** implementation rebuilt the README status (Earlier work rolled to #1–504 and #505–1016; Recent #1017–1022; Next rebuilt). Re-read the block before any README edit. Next item 3 (C200's lever) is research's call after C199 (c).
- **07:14 (#1023-#1024):** C199 h2: S_a 0.5145 (on-type gain +0.015, so mostly a greedy effect), S_b 0.4433 (Trainer loss −0.057, more than linear pricing's about −0.03 at k 4-6; a lead for the rule-9 replay). setA-rule9 done; setB-rule9 next, then (c).
- **07:15 (#1026):** C199 rule-9: S_b is starvation (attacks a turn 0.71 → 0.62, play rates normal, small Energy discards). Arm (c) greedy running since 07:15.
- **07:37 (#1028):** C199 closed. Arm (c) greedy −0.039 (R-price-persists by the point, strictly between); h2 −0.003 unreplicated. On-typing wouldn't free Trainer slots under greedy. Open levers: C189 and Evan's practice-deck rule.
- **08:05 (#1030):** C197 C49-sd column: seeds disagree (+6, −1), reported only. Asked to pause DN s51 so C189 gets RAM; it resumes after C189-cells.
- **08:06 (#1032):** DN s51 paused (STOP 08:06:19; checkpoints after 27-28; resume held until C189-cells). C189 SH (driver 27424) launches when RAM frees.
- **08:46 (#1034):** A175 between: partial rainbow compensation (total~off +0.55, +0.53; about 2 of 5 surplus slots). If C189 reads R-no-gap, next is prior-free in-side type exploration. Asked for WL s52 to get the next slot by reservation. Lesson, again: quote the entry number from the read-back after appending; I slipped twice today.
- **08:47 (#1035):** Special-Energy read: the surplus is all basic (+5 basic, −1 special against the lists); DCE lead (0.65-1.09 against the lists' 3.29), with C169's Special effect about 0 as caveat. C189 next.
- **08:49 (#1036-#1037):** WL s52's reservation applied (reserve_only; waits on RAM 8.0 GB while C189 SL trains). **C201** (`runs/probe/C201-dce-density/record.md`): 2 basics → 1 DCE + 1 own Trainer (and → 2 DCE), greedy, after C189's cells. DCE engine checks were done in C198 A3/A4; DCE proposed 1.2-1.5% and kept at base. Next free record: C202.
- **08:50 (#1038):** DCE not stack-cut (removal per copy 0.98-1.07); its low count is slow arithmetic. The env attach-path check for DCE was asked of implementation before C201.
- **08:50:** C201 Amendment 2: if R-density, the limit is exploration rate (about 230 iterations to the lists' DCE), so the next arm is block moves or a larger in-step.
- **08:52 (#1039):** C201 attach check A5 48/48 pass (DCE is provides [C] with provideAmount 2; implementation's first test was faulty, now fixed). Arms built (e: A 22, B 19 decks; f: A 21, B 18); median DCE 0. Greedy running on CPU since 08:52; h2 after C189-cells.
- **09:04 (#1041):** C201 greedy: S_e 0.4927 (level, between by SE), S_f 0.5121 (+0.012, about 1 SE). Density isn't a lever under greedy. C189 is the live lever; its SL ends about 09:18.
- **09:38 (#1042):** C189 SL done 09:16:48; cells launched 09:37:02, after an 18-minute refusal (a duplicate --pilot flag; monitors had hidden 'refused'). Hold gone. Priority by default: WL s52 resume, WR s50, C201 h2, DN s51.
- **09:40:** HOLD-SCREENS reserve_only WL s52 and WR s50 (hold_c193 pid 25416 removes it once both run); C201 setA-h2 running since 09:37:40; C189-cells running.
- **10:02 (#1046):** C189 stage 1 between, dividend leaning reverse (−0.017 greedy); specialists help both groups. Stage 2 reserved ahead of DN s51, ND s49, H0 s49; WL s53 first-come. If stage 2 agrees, the pilot lever (Trainer-specific skill) isn't supported, leaving coherence and Evan's practice-deck rule.
- **10:04 (#1047):** WL s52's resume ran 0 iterations (the chain had been reset to --iters 45 at about 06:39); now --iters 75 (queue_c191b pid 48344). Hold reserve_only WL s52, WL s53, C189 SH/SL s2 until C189-cells-s2. H0 s49 paused (STOP) to free its slot.
- **10:28 (#1050):** C201 h2: R-density by the point (0.5227), strictly between; the fourth depth-favours-Trainers/efficiency result. Open: edit-level searched selection (C197 tested deck re-ranking only).
- **10:32 (#1051):** C187's queue exited (pause-STOP gap); H0 s49 resumes via queue_c187b (pid 4576); queue_c90 fixed (STOP.resuming). DN s51 is still on the old queue_c184.
- **11:48 (#1054):** WL s52 to 74: G1 4.8 → 19.7 (transit confirmed), median 15/25/18, drift slowing, no stop. WR s50 at 44 median 20/13/27, G1 31. Asked for the best-12 shape, WR drift, and WR s51's status.
- **11:51 (#1056):** WL s52 best 12: lists' shape at 44 (13.5/29.5/17), then W-like (16/18/27 at 74); the third start to converge Energy-heavy. C191 set A R-attract by the letter, E* about 20.3 (between-band), confounded. Queue: WL s53 paused for C189 s2, then WL s53, then WR s51 on its own driver.
- **11:52 (#1057):** WL s53 paused (STOP 11:52; queue_c191d pid 9440); two-phase hold (pid 7036): C189 s2 first, then WL s53 and WR s51 (own driver queue_c184b pid 23828). Waiting on C189 stage 2, about 1.5 h.
- **12:45 (#1058):** A176 became **C202** (`runs/probe/C202-rerank-lists-like/record.md`): C197's re-rank on WL s52 at 44 and D s48 at 29, each with its own pilot; R-greedy-attractor against R-pilot-attractor. Beside C189 s2 or right after. README: block #1049–1056 closed (5 block bullets after #505–1016). Next free record: C203.
- **12:47 (#1059):** C202 built (c197_rerank.py gains --it/--out-dir/--read); G cells beside C189 SL-s49-s2; H cells after C189-cells-s2.
- **13:08 (#1061):** C202 greedy: WL s52 corr(z,T) −0.503 (strongest lean yet), D s48 −0.06. Amendment 1: T-only band (E noise 3); set 2 = WL s53 at 44; D's H dropped. WL s52 H running since 13:05.
- **13:09 (#1062-#1063):** C202 Amendment 2 in the read script; mean ΔT SE about 1.84 (2 SE about 3.7 copies). Power note added: pilot-attractor means 'no large shift'.
- **13:21 (#1065):** C189 stage 2: dividend −0.022 (about 2 SE below 0), replicated reverse lean; R-bias not supported. Stage 3 first-come after WL s53.
- **13:22 (#1066):** WL s53 resumed 13:21:52 (it 8). Phased hold (hold_phases.py pid 11864): WL s53 + C189 s48 stage until C189-cells-s48, then WR s51 (queue_c184b pid 46208). SH-s48 may wait for C202-s1-H (RAM 8.7 GB).
- **13:23 (#1068):** C202 set 1: R-pilot-attractor condition (median ΔT 0; mean +0.04, SE 1.35; corr −0.47). Set 2 at WL s53's 44. If it agrees, the levers are the pilot's learning and Evan's practice-deck rule.
- **14:57 (#1070):** WL s53 at 44: best 12 at 13.67/29.25/17.08 (G1 last 2.33), the lists' shape at both WL seeds at 44, a transit. Asked for G3 at 44 for both. C202 set 2 H running.
- **15:00 (#1072):** G3 at 44, WL s52 best 12: 0.2257 greedy (far under 0.5, about W's level). Shape match is a count coincidence; read G1 with G3.
- **15:04 (#1073):** G3 at 44 replicated: WL s53 0.2608 (s52 0.2257); lists-shaped but about half of parity.
- **15:08:** C202 set 2 H killed (5.6% of lines capped at maxSteps 40). Amendment 3: rerun at 80 (120 if needed), and the same for WL s53's G3 search halves; rule-9 check of long lines.
- **15:30 (#1078):** Env fault fixed (Energy Burn repeat-Power loop; env/legal.js), first seen in #831/#833 (11-02) and parked by research then. **Lesson:** fix confirmed rule-9 faults at the next clean boundary. C202 Amendment 4: both sets rerun under the fixed env at maxSteps 40. Completeness check asked (Alakazam/Slowbro pick loops). ar/ needs re-setup after the env change.
- **15:31 (#1080):** WL s52 best-12 G3 under search 0.154 (greedy 0.226, lists 0.505). Queue first-come: G3 s53, cap checks, C202 fixed reruns, then C189 s3 at about 17:30.
- **15:51 (#1082):** G3 under search replicated (0.143, 0.154). README: block #1073–1080 closed (8 block bullets after #505–1016, so the next close rolls up).
- **15:53 (#1085):** 4 of 2000 greedy games cap on cycling Powers (Energy Trans, Damage Swap, Slowbro); cycle rule built now, deployed after C202's reruns. Lists hold none of these Pokémon (checked).
- **15:55 (#1086):** cycle rule built in env_cycle/ (A7 PASS; 50/50, 38/38). Deploy after C202's fixed reruns. C189 Amendment 7: stage 3 starts after the deploy (one env).
- **16:22 (#1090):** C202 closed: between by the letter; means show no judge effect (+0.60, +0.04, SE about 1.5). Attractor is the pilot's valuation. Open: the pilot's learning (no cheap record with a case), Evan's practice-deck rule, C189 s3, C191 set B.
- **16:23 (#1091):** cap pods 0 hits under both fixes, so the rule-9 loops are closed. No deep round (topics covered, rounds 3-9). Waiting on C189 s3 and C191 set B. Usage 38% at 62% elapsed.
- **16:45 (#1092):** A177 became **C203** (`runs/probe/C203-lists-in-selection/record.md`): (a) the lists in W's populations, one z read; (b) a 30-minute frozen-pilot bench from the lists (D 24, turnover off). Rule check in the record. Next free record: C204.
- **16:52 (#1094):** C203 (a) R-explore-a at both seeds (lists 19-22 of 24 in the top quarter under W's own pilot); the strength gap is content exploration. (b) decides the Energy count; its freeze fault was fixed (Drafter.load lr).
- **16:54 (#1095):** Frozen-head look-back: only H0 used --draft-lr 0. H0 s48's head hash is constant 0-44 (lr 0.0), so #953 stands. **TODO:** re-check H0 s49's head hash at its next snapshot against 00fd38b3d6a7 (scratchpad head_hash.py; copy in C203's folder).
- **17:00:** C189 SH-s48 done 16:59 (fixed env); SL-s48 running. Order after C189-cells-s48: C203 (b) strictly before WR s51 (taken by default).
- **17:00:** three-phase hold: C189 s48 pilots, then C203 (b), then WR s51. WR s51's driver had a dead wait on WL s53 (ended at 44); removed and relaunched.
- **17:47 (#1099):** C189 closed: no Trainer dividend at either W seed (s48 −0.003/+0.002, R-no-bias sampled; s49 −0.022). C203 (b) next.
- **18:12 (#1101):** C203 (b) R-explore: from the lists, frozen selection holds counts (ΔE −0.08) and improves them (G3 0.566 against the originals). The attractor comes from the search's start and reach, not the judge's valuation. Replicate at s49 asked; next record is round 8's block moves.
- **18:13 (#1103):** C203 Amendment 1: (b3) turnover on, protect off, 2 stages: R-generator against R-start/reach. Then the s49 replicate and the s48 length stage.
- **18:13:** order agreed: C203 b-s49 (queued, W s49 frozen nets), then (b3), then the s48 length stage; DN s51 paused behind them, WR s51 running beside.
- **18:14 (#1104):** C203 Amendment 2: (b3) protect 20, lists born −20, 30 iterations (band at about 30).
- **18:19 (#1105):** b-s49, then b3-s48 (--lists-age 20, protect 20, 30 iterations, reads at 59 and 74), then bL-s48. WR s51 paused at 10 for RAM.
- **18:42 (#1107):** C203 (b) s49: R-explore on E replicated (ΔE +0.33); G3 0.594/0.569; but T −1.92 into P at s49 (head's cut). (b3) next, then bL.
- **19:24 (#1109):** (b3) at 14: E +2.38, 62% from turnover's kill (culls Trainer-rich lists), dilution 23%, edits 14%; list-rooted survivors at −5.8 T. One mechanism: the deck-level z penalizes Trainer-rich decks, lists included. Band at 74 (about 20:05).
- **19:25 (#1110):** **C204** (`runs/probe/C204-cull-end-causes/record.md`): culled against kept lists' end causes in (b3) (R-overdraw / R-tempo / R-score-fault). Read the scoring: round_score win 1, time-win 2/3, draw 1/3, loss 0; deck-out is a loss. Next free record: C205.
- **19:26 (#1111):** C204 Amendment 1: time-win 2/3 is the sourced STS rule (rules report, line 69); re-score sensitivity added; if sensitive, check the clock, not the 2/3.
- **19:29 (#1113):** C204 built as a replay; z = round_score, with 0 mismatches. Minor: cut-off games get z 1/3 but reward 0 (rare after the fixes). The smoke leans overdraw (less deck left, more draws); full reads queued.
- **19:42 (#1115):** C204: R-overdraw among the lists (culled lists deck out 2.7× more, draw more, end with less deck). W's own culls aren't overdraw. Rule 9 clean; time sensitivity between, leaning cleared. Step 2 next: overdraw as misplay or as a shared blind spot.
- **19:43 (#1116):** **C205** (`runs/probe/C205-overdraw-branch/record.md`): branch test at draw-Trainer decisions by deck left; R-misplay against R-shared. Next free record: C206.
- **19:44 (#1117):** Deck count is in the obs exactly (tokens.js:191). C205 Am1: dose-response buckets, both pilots. C204 Am2: one seed; replicate under W s49's pilot before C205.
- **19:50 (#1119):** C204 replicate under W s49: 1.66×, between (direction replicated). C205 queued (4 × 25 min); pilot hint: Δ_play −0.128 at deck ≤ 10, play rate flat 0.17.
- **19:55 (#1121):** (b3) at 30: between (descendants +1.29 E). Contributors: kill +2.11, protected entrants +1.59, the head's T cut on lineages (−6.2 T). The day's synthesis is in the entry. Next: C205, bL-s48.
- **19:57 (#1122):** bL launches as a --resume of C203-b-s48 (queue_c193 resume form), first-come after C205's four seeds.
- **20:15 (#1124):** C205 interim (1/4): Δ_play −0.051 at deck ≤ 10 (5 SE), falling with deck size; play rate flat 0.17, so dose-response R-misplay is likely. Lever record after the full read.
- **20:45 (#1126):** A178 answered from notes by C113 (#497): longer clocks make the lists lose more (decking out), so the clock props Trainers up and overdraw dominates. DN s51 and WR s51 are paused by design. Lesson again: quote the number read back after the append.
- **21:35 (#1129):** C205 R-misplay under both pilots (dose form). **C206** (`runs/probe/C206-draw-mask-price/record.md`): an eval-only low-deck draw mask on C193's lists read; R-overdraw-prices against R-not-pricing. Waits for the GPU (Evan's apps at 15.6/15.9 GB; GPU-PAUSE not set and not touched). Next free record: C207.
- **21:37 (#1130):** C206 Amendment 1 (M10 primary; reach-0.50 also needs ≥ 2 SE lift). C207 pre-read: deck-outs 1.57-1.92% of W's training games, so the lever is exposure (a longer practice clock) if C206 reads R-overdraw-prices.
- **21:36:** C207 design notes in C206's record: a quarter of practice untimed; the encoder sees the turn (tokens.js:186), but whether it sees cap T or a timed flag is unchecked; no-Pokémon endings (48-56%) to look at later.
- **21:37:** C207 note 3: clock inputs (timed bit and cap or turns left); arm A (inputs only) against arm B (inputs plus a quarter untimed) to separate the input effect from exposure.
- **21:40 (#1131):** C206 built (eval-only drawMask in runner.js and remote_worker.js; masked cards 0 plays; dry run identical), queued ahead of bL. Held by row 73: free RAM 0.8 GB, GPU 15.5/15.9 (another project's pid 12420 9.2 GB plus Evan's apps), none ours.
