# Notes for Claude

## Progress log and README status

Whenever you finish a todo (a task, a plan step, or anything checked off in a todo list), do
both of these before moving on to the next one:

1. **Append an entry to `notes/progress-log.md`**, in the format at the top of that file.
2. **Update the README status** from the log, between `<!-- status:start -->` and
   `<!-- status:end -->` in `README.md`.

The log is the full record, and the README status is a recursive summary of it, following Wu et
al., *Recursively Summarizing Books with Human Feedback* (2021). The log plays the part of the
book text. As in the paper, no summary ever reads more than **8 items** at once:

| Height | Where | Summarizes | Length cap |
|---|---|---|---|
| 0 | `notes/progress-log.md` entries, numbered #1, #2, … | The actual work: diff, test output, measurements | One entry per todo |
| 1 | README **Recent** | The open log entries not yet rolled into a block (at most 8) | 3 sentences |
| 1 | README **Earlier work**, one bullet per closed block | That block's log entries only (at most 8) | 3 sentences |
| 2 | README **Earlier work**, a rolled-up bullet | 8 block bullets | 3 sentences |
| top | README **Where things stand** | The Earlier work bullets plus Recent | 5 sentences |

**Writing the log entry (height 0).** Write it from the source (the diff, test output, notes),
not from memory. Number it one more than the last entry. The log is append-only: never edit or
delete past entries; if one was wrong, add a new entry that corrects it.

**Updating the README:**

- **Recent:** recompose from the open log entries, with the latest Earlier work bullets as
  context so it doesn't repeat or contradict them. Label it with the entry range ("log #9–12").
- **Closing a block:** when the open entries reach 8, or a milestone finishes (a chapter break,
  so blocks don't span milestones), write one Earlier work bullet from those entries alone,
  labeled with the range and milestone, and empty Recent.
- **Rolling up:** when Earlier work reaches 8 block bullets, replace them with one bullet that
  summarizes those 8 bullets. Do the same at any height that reaches 8.
- **When a milestone finishes:** also mark its heading in the Plan "— ✅ done", as A0 is.
- **Where things stand:** recompose from the Earlier work bullets plus Recent.
- **Next:** the next 3–6 todos in order. Build it from the plan (A1.2, A2, …) and the **Next**
  and **Found** lines of recent log entries. Next is rebuilt each time, not summarized.
- Set the *Updated* date to today.

**Guarding against the paper's failure modes:**

- *Errors compound up the tree.* Only the log reads the source, so its entries must be exact:
  real numbers, real test counts, and "partly done" or "not verified" where that is true. A
  higher level never adds a claim that isn't in the level below.
- *Small details that add up get dropped.* If something recurs across log entries (a flaky
  test, a growing throughput gap, a rules question that keeps coming up), say so in the
  block summary even if no single entry made it look important.
- *Lists instead of summaries.* Summaries say what the work adds up to, not a list of events.

Edit these files only; don't commit or push unless asked.

## Submodule

`ryuu-play/` is a submodule pinned to `AI-Alignment-UIUC/ryuu-play` on `sts-2000-pool`. In a fresh clone,
run `git submodule update --init --recursive` first. Engine changes are committed in the
submodule, and then the pin is bumped here.
