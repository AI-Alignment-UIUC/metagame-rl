# One unattended round of the loop

`notes/scripts/loop.py` (the supervisor, log #176) started this session, not Evan, and nobody is watching. Do one
cycle of the method, write the handoff, and exit. You are fresh: everything you know comes from files, so read them
rather than assume. A round is about an hour of work at most; the supervisor ends a round at 120 minutes.

## 0. The goal (Evan's standing directive, restated 2026-10-24)
- **The ground truth.** The 24 STS 2000 lists (median 13.5 / 28 / 18 Pokémon / Trainers / Energy, 8 archetypes) are
  optimal. Success is the loop relearning that metagame from random decks and its own play, with nothing human in
  training (method §2). A consistent deviation (more Energy, fewer Trainers, one deck type) means part of the process
  is wrong, never the lists. Read the Ground truth table in `state.md` before anything else.
- **Stay out of local minima.** Evan, 2026-10-24: "try to avoid getting in local minima. Remember the ground truth
  again." The research loop collapses the way the decks do: prefer an experiment that can rule out a rival over one
  more flag on the incumbent, keep the floor, and when results stall, take a different mechanism from an untested
  family rather than a variant of the last run.
- **GPU, not tokens.** Evan, 2026-10-24: "just use the GPU rather than API." Spend the night on GPU runs: keep the
  slots full, keep rounds short, use subagents only where §2 asks for them, and run no outside-research round unless
  a §12 trigger fires.

## 1. Read first
1. `runs/loop/state.md`: why you were started, live and ended runs, the floor, the last handoff, README Next,
   Evan's open requests.
2. `notes/method.md`, all of it. Its §1 (session start) is this round's checklist, with the changes below.
3. `notes/hypotheses.md` lines 1-42 and §7 (the Queue), then the families your decisions touch (grep by H id).
4. The last 3 entries of `notes/progress-log.md` in full, the README status block, and new rows of
   `notes/evan-requests.md`.
5. The memory index `C:/Users/evanc/.claude/projects/C--Users-evanc-Desktop-333/memory/MEMORY.md`, and the notes it
   names that bear on this round.

## 2. The cycle (method §1 steps 2-6, §6)
1. **Log debt first (§13).** Each run under "Ended, not yet logged": read its logs and record, score it against the
   record's bands, write the log entry (CLAUDE.md format, from the files), update `hypotheses.md`, the README status
   (CLAUDE.md's rules) and the run's `evan-requests.md` row; then `loop.py ack <id> "#nnn"`. A run the log's Next
   expects but that never ended cleanly (no end line, no process) is "killed by machine" (§9): log it and relaunch it
   if its record still stands.
2. **Live runs (§9).** At each look reached, apply the record's kill rules on the run's own readout; a run that is
   decided, futile, harmful or inert stops now: `loop.py stop <id>`. Log any look that decides something.
   `state.md` lists each live run's iterations with game errors. A lone game error is a warning: read its traceback in
   the run's `stdout.log` and log it. A record's errors kill fires when errors recur: a second iteration with errors,
   or 3 or more in one (Evan, log #232).
3. **Free slots (§6 order).** Evan's ideas first (state.md, "Evan's open requests"). For a new candidate, first get
   proposals from a fresh `lean-lead` subagent. Its brief points only at `hypotheses.md` lines 1-42, §4-§5 and §7,
   the do-not-repeat lists of the families involved, and Evan's open rows, not at the recent log entries (recent
   results anchor proposals on the incumbent), and asks for 3 candidates, each with its rivals' bands, cost in dh, its
   3 nearest past tests and its start class, at least one of them a prevention start and one from a coverage-table
   gap or an untested family. Then check each yourself: the §5 near-duplicate rule (grep the log,
   notes and `git log`) and §6 admissibility. Choose one, or fall back to §6's "no idle slot" order.
4. **Launch only through `loop.py launch`.** Write the record first (§10 format) as `record.md` in the run's folder,
   and the chain script beside it, then:

       .venv/Scripts/python notes/scripts/loop.py launch <run id> --candidate C50 --record <run>/record.md \
           --kind screen|pilot|probe --start escape|prevention|other --from <checkpoint>|fresh \
           [--components a,b] [--looks 139,159] [--progress <trainer folder>/log.jsonl] [--evan-row N] \
           [--replicate-of <run id>] [--resume] -- sh <run>/chain.sh

   `--progress` is needed when the chain trains in another folder than the run id's; `--looks` when the record names
   snapshot iterations; `--look-wait 30` when the run's own watcher reads each look (its readings land about 25
   minutes after the snapshot). If it refuses, change the design. Never start training or a probe another way, and never
   work around a refusal. New code paths get a tiny smoke run before a launch uses them. GPU audits and smokes are
   launches too (`--kind probe`; `--gpu-gb 0` for a CPU-only one).
5. **Machine.** CLAUDE.md's limits (80% of GPU memory and compute, at most 16 threads) and #175's: at most one
   probing trainer beside a metagame screen. `loop.py launch` checks slots, free RAM and GPU memory.
6. **Integrity.** Before a log entry announces a new best, a milestone or an adoption into R0, a fresh `lean-reader`
   given only the diff, the record and the chain checks for: human lists entering training (§2), edits to the
   frozen files, readouts that could be gamed. Its verdict goes in the entry.
7. **Outside rounds (§12).** When a trigger fires, run at most one, with `lean-reader` subagents (at most 3 pages
   each), logged as its own entry; anything larger goes to README Next.

## 3. Never (Evan's limits for unattended rounds, log #176)
- Any git write (commit, push, reset, checkout, clean, stash); deleting or moving run data (STOP files only).
- Changing the training rules of method §2, the game's definition, `notes/method.md`, `notes/round.md` or
  `loop.py`'s limits. Propose these in README Next as "Decision for Evan" with one line of evidence.
- Editing the frozen files (`rl/answer_key.py`, `notes/data/2000-super-trainer-showdown-california/`); the supervisor
  halts the loop on any change.
- Asking questions: nobody answers. Decide, log the reason, carry on (§11).
- `cd`, or waiting in a sleep loop. Paths are relative to `metagame-rl`. Long work runs detached through
  `loop.py launch`; the supervisor starts the next round at the next look or end.
- Retrying a command the permissions denied, in any form. Note it in the handoff instead.
- Switching the loop: `loop.py pause`, `resume`, `disable`, `enable`, `round` and `rehash` are Evan's (log #232);
  `loop.py` refuses them in a round.

## 4. Dry runs
If the prompt says DRY RUN: read and decide as in §1-§2, but change nothing outside `runs/loop/`, and launch, stop
or ack nothing (`loop.py` refuses them in a dry round anyway). Write `runs/loop/dry-plan.md`: the log entries you
would write (full text), each launch with its record and full command, each stop, and the ledger and README
changes. Then write the handoff.

## 5. End
1. The log, `hypotheses.md`, the README status and Next, and `evan-requests.md` agree (method §1 step 6).
2. Write `runs/loop/handoff.md`, at most 30 lines: what this round did (log numbers), what is live and when its next
   look is due, what the next round should do first, decisions waiting for Evan (also in README Next), commands
   that were denied.
3. Final message: three lines (did / live / next).
