# Branched returns at prompts: design only (waits on Evan's decision 1, log #264)

Not in train.py until Evan rules on row 60 ("don't train on the oracle answers"). Written 2026-10-26 for the day's
plan (#264 item 2).

**What.** During collection, at a share p of prompt rows inside the deciding seat's own Trainer, branch every legal
answer (up to k = 8). Play m rollouts of the pilot's own sampled play from each, either to the game's end or to the
end of the turn scored by V, with common random numbers. That gives Q-hat(s, a) for every answer: the A1 machinery,
run during training. Two ways to use it, which differ for row 60:
1. **As value targets only (vine; TRPO's "vine" estimator, Schulman 2015, from memory).** Q-hat trains P2's Q head
   (ar/ideas.md), and the policy moves only through the expected gradient (P3) on that Q. Nothing imitates a chosen
   answer; the targets are the pilot's own returns, branched. Closest to "learning itself".
2. **As soft policy targets (AlphaZero / ExIt).** softmax(Q-hat / tau) over the answers, through C49's existing KL
   term, as the main-phase search targets already are. The policy imitates the search's preference: nearer to what
   row 60 excluded, though the search is the pilot's own play, not an outside oracle.

**Where.**
- In the worker: extend `env/remote_worker.js` probeCatch, which today returns early on any prompt
  (`if (g.decision().prompt ...) return`), to branch prompt rows inside the seat's own Trainer.
- Reuse C73's PromptOracle line-playing (`env/tools/probe_oracle_worker.js`) and the staged followups replicate code.
- train.py reads the branched scores as `probe_c` / `probe_q` at those rows.
- It is an env change, so ar/ needs a re-setup.

**Cost (estimate).** k x m rollouts per branched row. At p = 0.02 of about 30 prompt rows a game, k = 8, m = 4 to the
end of the turn, it is about 20 extra lines a game, the size of C49's main-phase probe (p 0.05, k 4, dets 4).

**Gate.**
- A1 must show real spread (G >= 0.01, > 2 SE) for the Trainers it targets.
- With (a), the critic seeing the target, P1 comes first and this is not needed.
- With (b), it makes P2's Q targets exact instead of sampled: it is P2 with lower variance, run after P2 if P2 is too
  slow.
