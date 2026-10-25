# followups: Q-max over a Trainer's follow-up answers in the C49 search (opt-in)

Apply from the repo root: `git apply env/staged/patches/followups.patch` (touches env/agents.js, env/remote_worker.js).
Test after applying: `node env/staged/patches/test_followups.js` (stub pilot; no GPU or Python).

- Flag: `cmd.probe.followups = { n }`; absent or n <= 1 is byte-identical to now (same rng draws, stats, scores).
- Semantics: each (candidate, copy) line is run n times on the SAME re-dealt copy (same clone seed; under crn the same
  seeds for every candidate). Replicate 0 is the greedy line. Replicates 1..n-1 differ only where a prompt is open for
  the deciding player while their own Trainer resolves (game.chain.key 'trainer|..', the X1 test of
  env/tools/probe_worker.js): the answer is uniform over the legal options but 'cancel', from an Rng of the line's seed.
- The copy's score is the max over its n replicates; the mean over copies, the best move and the keepLines scores (still
  one value per copy) all use it.
- stats gain `followupLines` (replicate lines run, not counted in `lines`) and `followupPrompts` (prompts sampled).
- Cost: n times the lines (and pilot rows) at every probed decision, not only Trainer candidates. Replicates of
  non-Trainer moves are identical to replicate 0, so a later pass could skip them if the cost matters.
- Enable from ar/train.py: `PROBE = {..., "followups": {"n": 3}}`.
- Caveat: the max biases Trainer scores upward (the optimiser's curse: the best of n noisy answers), while other moves
  keep their single greedy line. Screen over several seeds before adopting, against n = 1 and a no-bias control.
- A replicate (r >= 1) that hits maxSteps is left out of the max (its 0 would beat a negative greedy score); replicate 0
  keeps today's rule (capped scores 0), so n = 1 is unchanged.
- Training with it is pending Evan's call on his row-60 rule ("don't train on the oracle answers"): the policy is still
  trained only on the main-phase choice; the follow-up answers are never trained on.
