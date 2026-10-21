# Evan's messages: what was tried

Every message from Evan, quoted, with what was done about it. Updated in the same turn a new message is acted on
(Evan, 2026-10-19: "Opt for trying fully out the ideas that I give and logging them, rather than continuing with what
was going before. I'd like a log of all of the messages I sent that you tried and didn't try.").

Status: **tried** (built and measured), **partly** (built, or measured only in part), **not tried**, **rule** (a standing
instruction, followed from then on), **answered** (a question, answered with data).

Sessions before 2026-10-19 are listed as the progress log and the assistant's memory notes recorded them. Messages that
neither recorded are missing, so this part is incomplete.

## 2026-10-19 (this session, verbatim)

| # | Message | Status | Where | Outcome / why not |
|---|---|---|---|---|
| 1 | "Continue with the automated metagame rl design" | tried | log #86–91 | The lab was found stopped. A restart bug and the rebase gap were fixed, it was restarted, and the A/A cards set the bars. 2 PPO epochs and 6 swaps a draw were adopted; auxiliary heads and value cross-attention failed. |
| 2 | "Are they using trainers now?" | answered | log #92 | Not really. At 220 the median deck had 2 Trainers and 16 of 99 decks had none (12 at 200; the human lists have 28). |
| 3 | "We want to figure out why there are no trainers, and if not, what is wrong with the pilot that it can't use trainers" | tried | log #92 | Every pilot does better with basic Energy than with search, disruption or tempo Trainers, pilots trained on the human lists included. Its setup-before-attack fails: Trainer-first lethals at 58–61% (attack lethals 86–94%), PlusPower lethals at random's 31%, and it attacks less often after PlusPower and Gust than on an average turn. The drafting follows the pilot, and its incoming choice has collapsed. |
| 4 | "Trainers are certainly good and we can treat the human lists as ground truth, in the sense if it is using way more energy then it isn't correctly drafting or playing." | rule | log #92, memory | Results are now read this way: Energy beating a Trainer means the pilot misplays the Trainer. |
| 5 | "It should probably practice each deck it drafts before playing it in a setting that counts towards reward" | partly (built, being tested) | log #93 | `rl/metagame.py --season K --candidates C`. Lab cards `008a-meta-practice` (season 5, 4 candidates) and `008b-meta-practice10` (season 10, 2 candidates) started at 240, ahead of everything else. 008a failed at 270 (answer key +0.023 against 0.03, pilot −23 Elo, best decks still Energy-heavy, log #100). 008b passed its answer-key rule at 280 (+0.049) but its best decks were further from the human shape (10 Trainers / 30 Energy against the main line's 19 / 25), so I held it before adoption for Evan's call (log #101). |
| 6 | "Opt for trying fully out the ideas that I give and logging them, rather than continuing with what was going before. I'd like a log of all of the messages I sent that you tried and didn't try." | rule | this file, memory, log #94 | Evan's ideas go ahead of the queue, each with a stronger variant. My cards (entropy 0.02, slot binding, learning rate 2e-4) wait behind them. His untried memory and deck-encoder ideas are now lab cards (`009-pilot-*`), held so they do not disturb the practice cards; the lab runs 4 branches. |
| 7 | "Now synthesize my comments and all of the previous tests into a new iterative plan for finding a metagame and game agent architecure and training system that will rediscover the ground truth of the human decks. We can assume if the agent is sufficiently off from the human decks (ie, way more energy), then it is not learning something correctly. Then I will review this iterative plan that should continuously optimize for this goal." | tried (approved, message 10) | `notes/plan-rediscovery.md`, log #94 | A scorecard (pilot competence, strength, deck shape, answer key, drafting health) with targets; a loop that fixes the largest gap upstream first (pilot before drafting); stages A–D; five questions for Evan. |
| 8 | "Show me the plan" | answered | — | The plan printed in full; I corrected one line (the S2 "now" value was the pilot on its own decks, not on the human lists). |
| 9 | "Simplify to three stages with three steps each" | tried (awaiting review) | `notes/plan-rediscovery.md`, log #95 | Rewritten: (1) the pilot plays the human field's cards correctly, (2) the drafting finds the human deck shape, (3) rediscover from scratch, then held-out 2005 and Magic; three steps each, a six-row scorecard, four questions. |
| 10 | "Sure try it" | trying | log #96 | Read as approval of the plan and of its four questions as proposed: prize shaping kept on, Knock Outs and prizes inside the turn search, pilot changes decided on the puzzles and the Trainer-value panel with 2005 held out, and the targets as written. Stage 1 step 2: play-time search over the pilot lifts Trainer-first puzzles 60 → 85–88% and PlusPower 31 → 81%; expert iteration built and queued (two variants), with turn-level credit, prize shaping kept on and entropy 0.02; pilot cards now decided on a competence score (A/A bar 0.06). |
| 11 | "synthesize progress and push, continue with the plan, might have gotten interrupted" | tried | log #104–105, README, commits | It had been interrupted: the lab died with the previous session at 21:44 (deckcross-w at 284 of 290). `rl.lab start` now launches it outside the session; two races that dropped hand edits were fixed (the competence bar had silently fallen to 0.03; restored to 0.06, no decision affected); the deck-free card's hold was lifted, as the practice cards it was held for are decided; the lab restarted at 22:15; README block #97–104 closed; pushed. Continued: at 290 the deck-free encoder was adopted, expert iteration at 0.3 and in-turn λ = 1 failed (#105). |
| 12 | "Sure do that" (to the two recommendations below) | trying | log #120 | (1) `008b-meta-practice10` closed as failed on deck shape. (2) The league: `rl/metagame.py --draft-heads`, 3 draft heads sharing the one pilot, each drafting and turning over its own third of the population; a deck-type count that tells the human archetypes apart (Pokémon overlap: the 24 lists make 3 types, the main line 1 since 160). Two cards from 400, decided at 480: `017-meta-league3` (the main head plus two fresh ones) and the variant `017-meta-league3-copy` (three copies of the main head). |
| 13 | "You should iterate in a deep thinking loop about how to improve, and try many different ideas. The goal is human type decks rediscovered. Get out of the local minima" | trying | log #127– | Started 2026-10-20 22:10: a diagnosis of why every line ends in one Energy-heavy type, then several escape ideas built and screened in parallel (see the log entries from #127). |

Decided 2026-10-20 (row 12): both decisions that were open here. (1) `008b-meta-practice10` (practice in seasons of 10) is closed as failed on deck shape. (2) The larger change the stall rule called for (log #116) is the league of draft heads, which revises his choice of one population with one draft head (#67): the population and the pilot stay one, and the draft head becomes three.

## Earlier sessions (as recorded)

| Date | Message (as quoted in the log or memory) | Status | Where | Outcome / why not |
|---|---|---|---|---|
| 10-05 | Autonomous work through all of Phase A, logging progress | rule | memory | Followed. |
| 10-05 | Move the repo to the AI-Alignment-UIUC org and rename it (for MTG later); keep the engine fork on the personal account | tried | memory | Done. |
| 10-06 | Keep jobs at about 80% of the machine (after 3 crashes) | rule | CLAUDE.md | `rl/limits.py`. |
| 10-06 | Forced Energy→Trainer swaps "defeats the purpose of self discovery" | rule | memory | No card-specific moves in search or training. |
| 10-07 | Rescope: Pokémon first (2000 → Worlds 2005), then MTG; cross-attention deck encoder deferred to Phase B | rule | memory | Followed (the deck encoder was later wanted earlier, 10-13). |
| 10-09 | "We want to do self-discovery and not build in experience. The point is to create a general method for TCGs, not solve PTCG on this narrow format." | rule | log #51, memory | No archived lists or bots in training; they are evaluation only. |
| 10-12 | Rewrite the meta level as one procedure ("drastically simplify using Occam's razor") | tried | log #64–65 | `rl/draft.py` and `rl/metagame.py`; the old code is at the `pre-simplify` tag. |
| 10-12 | Every card may change in a draw ("it might get stuck in local minima"), drawn at random; the picks use the game knowledge (through the pilot's encoder) | tried | log #65 | Built as asked. |
| 10-12 | The draft reward: result plus the prize margin (Evan's choice) | tried | log #66 | Margin 0.5. The result alone was tested later (lab 006: failed the answer-key rule, pilot +30 Elo; replication 006-n running). |
| 10-12 | One population with one pilot and one draft head, instead of per-agent heads (Evan's choice) | tried | log #67 | `runs/meta-99`, now the lab's main line. Revised by his choice on 2026-10-20 (row 12): a league of 3 draft heads, under test (log #120). |
| 10-12 | "it should obviously see every legal move" | tried | log #68 | Encoder bounds raised to 128 options and 256 tokens; overflow is now an error. |
| 10-12 | "do some ablations on the pilot architecture and training procedure" | partly | log #70 | Built (11-run chain); stopped after 2 runs when Evan moved to architecture improvements (next row). |
| 10-12 | Iterative architecture improvements: "where does it make sense to add cross or self attention" | tried | log #71–74 | Slot binding, option self-attention and ability text, screened at 40 iterations: all within the seed noise. |
| 10-13 | "make sure the input game state is a good representation regardless of the deck, and then combined with cross attention on deck to get the deck specific state" | tried | log #72–73, #98, #100, #104–105 | `deck_mode cross`, screened once from scratch at 40 iterations (within noise). In the lab, grown deck-blind it was stopped after one segment (−54 Elo, the handicap). Warm-started (`rl/warmstart.py`) it led on all three readings (+36.6, +20.9, +34.9 Elo), was even on the human lists (+5.4), and was **adopted at 290**: the main line is now deck-free, carrying a population at 10 / 29 / 21 Pokémon / Trainers / Energy. |
| 10-13 | Put gae1 (lambda 1) before the evaluation (Evan's choice) | tried | log #73 | lambda 1 learned much more slowly. |
| 10-14 | "I think the gradient signal is not reaching back? Can you also measure this" | tried | log #75 | Credit probe: the training signal at lambda 0.95 carries 56–75% of a move's effect, the value's one-step change 14–36%. |
| 10-14 | "Did you try any ablations for memory?" | tried | log #76, #79, #94, #99, #103 | Built in #76, parked in #79, run in the lab from 240: history tokens failed on the competence score (−0.016), the attention memory was stopped as clearly worse (−18 Elo), and the GRU memory was clearly worse at 280 (−21 Elo). All three forms negative. |
| 10-15 | "Try cross attention for the value head" | tried | log #77–78, lab 003 | Worse on a frozen trunk (#78); trained with the trunk in the lab, −1 Elo (failed, #89). |
| 10-15 | "Or maybe we should bootstrap from existing knowledge?" | tried | log #77, #81–82 | base-cont (base it79 continued) and vq4-cont; base-cont's 40 more iterations gave +55 Elo. |
| 10-16 | Stop the chain | tried | log #79 | Stopped at 00:22. |
| 10-16 | "Go look through the commits and see if you tried what you are currently trying" | rule | memory | The log and commits are searched before an experiment is proposed. |
| 10-16 | "it should be greedy then within the game. I just don't know how it will explore all of the combinations of play interactions then?" | tried | log #81–82 | Mostly greedy collection (`--explore 0.1`) lost by 116 Elo against a plain continuation; exploration is what teaches Trainer timing. |
| 10-18 | A plan to test architectures and metagame setups autonomously, without getting stuck in long runs | tried | log #83 | The lab (`rl/lab.py`, `notes/plan-lab.md`). |
| 10-18 | "Do 1/3 GPU so I can use it but keep iterating. The constant though is that the method should generalize to other card games, and that the ground truth is rediscovering the meta through playing the decks that it drafted, reusing learnings from the game in the meta drafting" | rule | log #83, plan-lab | `RL_GPU_SHARE=0.333`; every card states its generality; the main line is the metagame loop itself. |

## Not tried yet, to be tried fully

None open. The memory forms (10-14) were all tried and all negative (log #99, #103); the deck-free board encoder (10-13)
was adopted at 290 (log #105).
