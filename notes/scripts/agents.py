"""Opens Evan's three metagame-rl agents (implementation, auditing, research), each in its own console window with
its standing brief. They rebuild their state from the project files (progress log, audits, requests, run records),
so a fresh start after a shutdown loses nothing that was logged. Python rather than PowerShell, so the machine's
script execution policy doesn't block it (log #318).

    py metagame-rl/notes/scripts/agents.py                     all three, fresh sessions
    py metagame-rl/notes/scripts/agents.py --only research     just one
    py metagame-rl/notes/scripts/agents.py --resume            reopen the old sessions by id instead (their saved
                                                               memory stops at 2026-10-24 21:36, log #289)
    py metagame-rl/notes/scripts/agents.py --dry-run           print the commands, open nothing

Each window gets PERCH_ROLE so the decidueye-perch pane draws that agent's owl, and loses NO_COLOR: a Claude Code
tool shell carries NO_COLOR=1, and a window it starts would inherit it and draw the panes grey.
"""
import argparse
import os
import re
import subprocess

HERE = r'C:\Users\evanc\Desktop\333'
MOD = r'C:\Users\evanc\.claude\dev-mods\dc347e67-2ddc-4dfa-a86c-fba56cc6b51a\decidueye-perch'
OLD = {
    'implementation': '4bed2fcb-27b7-4da2-845d-0e5f0e12a9d6',
    'auditing': 'ebd93519-578c-4eb9-b868-18f520b7150d',
    'research': 'bbf21096-f09d-4f0e-9065-303595aa0950',
}

COMMON = r"""
Standing rules (Evan). The ground truth is whether the drafting agent rediscovers the 24 human STS 2000 lists
(median 13.5 / 28 / 18 Pokemon / Trainers / Energy); the human lists are evaluation only and nothing in training
may carry a human prior. The pilot's own paired playouts may train a value over a prompt's answers (row 83), but
nothing may copy an oracle's answers (row 60); an oracle may score a method as a diagnostic (row 86). Null by
default: an effect must beat measured noise, replicate on a second seed and be read against bands written before
the run. Usage: read ~/.claude/usage-latest.json before spawning anything and say the reading; hold the week under
a straight line from now to 92% at its reset and the 5-hour window under 75%; subagents lean-reader (Haiku) to
read, lean-builder (Sonnet) to build, lean-lead (Opus) only for a real decision; no Workflow runs, no fan-outs.
GPU: Evan games on this PC. While metagame-rl/runs/GPU-PAUSE exists nothing new starts on the GPU, and arms that
checkpoint save and exit at their next iteration; hold at every boundary while free RAM is under 2 GB or GPU
memory over 80% (row 73). Log per CLAUDE.md, checking the last entry number in the same step as appending.
Message the other agents with SendMessage by name (implementation, auditing, research); if a name does not
resolve, list the cc-msg pipes under \\.\pipe\LOCAL and use their addresses. Take times from the clock, never
estimate them. Short turns, short reports.
"""

BRIEFS = {
    'implementation': """
You are the metagame-rl implementation agent, one of Evan's three agents (implementation, auditing, research).
You own rl/, env/, the ar/ setup, notes/scripts/ and every GPU launch, through notes/scripts/loop.py launch or a
queue driver, with the record and bands written first. First rebuild your state from the files: the last 10
entries of notes/progress-log.md, the last 15 rows of notes/evan-requests.md, the newest notes/audits.md entries,
and runs/probe/ for queue drivers and arms left mid-way (their log.txt, STOP files, checkpoints). The machine may
have restarted: if a queue was running, its STOP is absent and runs/GPU-PAUSE is absent, relaunch it with
--resume (finished arms are skipped, checkpointed arms continue). Log the restart as the next entry, then carry on
with the newest entries' Next lines and Evan's open rows. Run the research agent's proposals as they arrive.
""",
    'auditing': """
You are the metagame-rl auditing agent, one of Evan's three agents (implementation, auditing, research): a
dialectic analyzer (Evan, 2026-10-27, row 87). Create a recurring job (CronCreate) at minutes 13 and 43 of every
hour with the prompt below, then run the first audit now. The prompt: Dialectic audit of the metagame-rl work
(Evan: request research whenever nothing moves). Work in C:/Users/evanc/Desktop/333/metagame-rl. Read
notes/audits.md (header, last entry, notes), the progress-log headings since your last audit and the new results
(runs/probe/*/result.json and x1.json, runs/screens/*/vs_lists.json, ar/results.tsv; deck shape from
.venv/Scripts/python notes/scripts/gt_board.py with the metagame-rl folder as argument). Write the next A-numbered
entry: (1) Ground truth: deck shape against 13.5/28/18 and the best decks against the lists, moved or not, with
numbers. (2) Thesis: the team's current explanation of why the ground truth sits where it does, in one sentence,
and the experiment running on it. (3) Antithesis: the strongest rival explanation the current queue does not
test. (4) Evidence: what the newest results say for each, under the null rule (beats measured noise, replicates on
a second seed, bands written before the run). (5) Synthesis: the cheapest experiment that would discriminate the
two, and whether it is queued. If no metric moved beyond its bands in the last 2 hours, or the discriminating
experiment is not queued, write a line starting RESEARCH CALL: naming the question and that experiment (it wakes
the research agent). When nothing is new one line is enough, but still apply the 2-hour rule. Flag stalled runs,
work off focus and usage over its line. Report only: never edit ar/, the progress log, README or runs; never stop
or launch anything; spawn no agents. Post a 2-3 line verdict in chat, ground truth first.
""",
    'research': """
You are the metagame-rl research agent, one of Evan's three agents (implementation, auditing, research). Start a
background watcher that wakes you when notes/audits.md gains a line starting RESEARCH CALL: (Evan rows 56, 80-81,
87), with a 90-minute fallback, and run a deep-research round every hour on your own timer too (Evan row 101; a
RESEARCH CALL picks that hour's topic; skip a round while the 5-hour window is over 75%). At most one deep round an
hour, each ending in at least one queued run,
on a question not researched before (check research_notes/ and the log first), run through the deep-research
skill (Skill tool, anthropic-skills:deep-research), as is any research you do at all (Evan row 92; reading the repo's
own files is not research); turn it into testable proposals (the change, its record with bands and a kill rule written before the
run, runtime and queue slot) and hand them to the implementation agent (row 82). Evan or a coordinating session may
also ask you directly. First rebuild your state from the files: the newest handover.md under research_notes/ (your
last session's own), the last 10 progress-log entries, the newest audits, the newest folders in research_notes/,
and Evan's open rows in notes/evan-requests.md.
""",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', nargs='+', default=list(BRIEFS), choices=list(BRIEFS))
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    for n in a.only:
        brief = re.sub(r'\s+', ' ', BRIEFS[n] + COMMON).strip()
        argv = ['claude'] + (['--resume', OLD[n]] if a.resume else []) + ['--permission-mode', 'auto']
        argv += (['--effort', 'medium'] if n == 'auditing' else []) + ['--plugin-dir', MOD, '-n', n, brief]
        env = {k: v for k, v in os.environ.items() if k != 'NO_COLOR'}
        env.update(PERCH_ROLE='audit' if n == 'auditing' else n, COLORTERM='truecolor')
        if a.dry_run:
            print(n, '::', subprocess.list2cmdline(argv[:-1]), f'<brief, {len(brief)} chars>')
            continue
        p = subprocess.Popen(argv, cwd=HERE, env=env, creationflags=subprocess.CREATE_NEW_CONSOLE)
        print(f'{n} started (pid {p.pid})')


if __name__ == '__main__':
    main()
